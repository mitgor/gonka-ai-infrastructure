"""
Gonka.ai API Gateway — FastAPI application.

OpenAI-compatible proxy with auth, rate limiting, usage metering,
model routing, and SSE streaming support.

Usage:
    uvicorn gateway.main:app --host 0.0.0.0 --port 9000
"""

import asyncio
import json
import time
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from config.settings import get_settings
from gateway.auth import AuthManager, extract_api_key
from gateway.errors import (
    backend_unavailable,
    generic_exception_handler,
    openai_error,
)
from gateway.metering import UsageMeter, UsageRecord
from gateway.rate_limit import RateLimiter
from gateway.router import ModelRouter
from agent.sessions import SessionManager
from agent.memory import MemoryStore
from agent.webhooks import WebhookManager
from agent.routes import router as agent_router, init_agent_routes
from agent.tiering import ModelTiering
from admin.api import router as admin_router, init_admin_routes
from serving.health import HealthChecker

# ---------- App Setup ----------

app = FastAPI(
    title="Gonka.ai Inference Gateway",
    version="0.1.0",
    description="OpenAI-compatible API gateway for Gonka.ai model serving",
)

settings = get_settings()
auth_manager = AuthManager(keys_file=settings.api_keys_file)
rate_limiter = RateLimiter()
usage_meter = UsageMeter(db_path=f"{settings.data_dir}/usage.db")
model_router = ModelRouter()
session_manager = SessionManager(
    ttl_seconds=settings.session_ttl_seconds,
    max_history=settings.session_max_history,
)
memory_store = MemoryStore(db_path=settings.memory_db_path)
webhook_manager = WebhookManager()
model_tiering = ModelTiering()
health_checker = HealthChecker(vllm_base_url=settings.vllm_base_url)

# Initialize agent routes with shared managers
init_agent_routes(session_manager, memory_store, webhook_manager, auth_manager)
app.include_router(agent_router)

# Initialize admin routes
init_admin_routes(auth_manager, usage_meter, model_router, session_manager, model_tiering, health_checker)
app.include_router(admin_router)

app.add_exception_handler(Exception, generic_exception_handler)


# ---------- OpenAI-Compatible Endpoints ----------


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    models = model_router.list_models()
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Proxy chat completion requests to vLLM backends.
    Supports both streaming and non-streaming responses.
    """
    start_time = time.time()

    # Auth
    api_key_str = extract_api_key(request)
    api_key = auth_manager.validate(api_key_str)
    if not api_key:
        return openai_error(401, "Invalid API key", "invalid_request_error", "invalid_api_key")

    # Rate limit check
    rate_limiter.check_request(api_key_str, api_key.rpm_limit)

    # Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return openai_error(400, "Invalid JSON body", "invalid_request_error", "bad_request")

    # Resolve model
    model_name = body.get("model")
    if not model_name:
        model_name = model_router.get_default_model()
        if not model_name:
            return openai_error(400, "No model specified and no default available",
                                "invalid_request_error", "model_required")
        body["model"] = model_name

    # Model tiering: auto-route based on content if enabled
    tier_hint = request.headers.get("x-gonka-tier")
    if tier_hint or not model_name:
        tiered_model = model_tiering.resolve_model(
            body.get("messages", []),
            requested_model=model_name,
            tier_hint=tier_hint,
        )
        if tiered_model:
            model_name = tiered_model
            body["model"] = model_name

    backend = model_router.resolve(model_name)

    # Agent session integration
    session_id = request.headers.get("x-gonka-session-id")
    if session_id:
        session_manager.get_or_create(session_id, api_key_str)
        body["messages"] = session_manager.inject_history(session_id, body.get("messages", []))

    # Forward to vLLM backend
    is_streaming = body.get("stream", False)

    if is_streaming:
        return await _stream_response(
            backend.backend_url, body, api_key_str, model_name,
            session_id, start_time,
        )
    else:
        return await _forward_response(
            backend.backend_url, body, api_key_str, model_name,
            session_id, start_time,
        )


async def _forward_response(
    backend_url: str, body: dict, api_key: str, model_name: str,
    session_id: Optional[str], start_time: float,
) -> JSONResponse:
    """Forward a non-streaming request to vLLM and return the response."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Forward with vLLM's model ID
            resp = await client.post(
                f"{backend_url}/v1/chat/completions",
                json=body,
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        return backend_unavailable(model_name)

    if resp.status_code != 200:
        return JSONResponse(status_code=resp.status_code, content=resp.json())

    result = resp.json()

    # Record usage
    usage = result.get("usage", {})
    latency_ms = (time.time() - start_time) * 1000
    usage_meter.record(UsageRecord(
        api_key=api_key,
        model=model_name,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        latency_ms=latency_ms,
        session_id=session_id,
        timestamp=time.time(),
    ))

    # Record tokens for TPM limiting
    rate_limiter.record_tokens(api_key, usage.get("total_tokens", 0))

    # Save to session history
    if session_id:
        # Save the user message and assistant response
        new_messages = body.get("messages", [])[-1:]  # Last user message
        choices = result.get("choices", [])
        if choices:
            assistant_msg = choices[0].get("message", {})
            if assistant_msg:
                new_messages.append(assistant_msg)
        session_manager.append_messages(session_id, new_messages)

    return JSONResponse(content=result)


async def _stream_response(
    backend_url: str, body: dict, api_key: str, model_name: str,
    session_id: Optional[str], start_time: float,
):
    """Stream SSE response from vLLM backend through the gateway."""
    total_tokens = 0

    async def event_generator():
        nonlocal total_tokens
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{backend_url}/v1/chat/completions",
                    json=body,
                ) as resp:
                    if resp.status_code != 200:
                        error_body = await resp.aread()
                        yield f"data: {error_body.decode()}\n\n"
                        return

                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                yield f"data: [DONE]\n\n"
                                break

                            try:
                                chunk = json.loads(data_str)
                                usage = chunk.get("usage")
                                if usage:
                                    total_tokens = usage.get("total_tokens", 0)
                            except json.JSONDecodeError:
                                pass

                            yield f"{line}\n\n"
        except (httpx.ConnectError, httpx.TimeoutException):
            error_data = {
                "error": {
                    "message": f"Backend '{model_name}' unavailable",
                    "type": "server_error",
                    "code": "backend_unavailable",
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"

        # Record usage after stream completes
        latency_ms = (time.time() - start_time) * 1000
        usage_meter.record(UsageRecord(
            api_key=api_key,
            model=model_name,
            input_tokens=0,  # Not available in streaming
            output_tokens=total_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            session_id=session_id,
            timestamp=time.time(),
        ))
        rate_limiter.record_tokens(api_key, total_tokens)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- Health ----------


@app.get("/health")
async def health():
    """Gateway health check."""
    return {
        "status": "ok",
        "models": model_router.model_count,
        "api_keys": auth_manager.key_count,
    }


# ---------- Dev: Bootstrap ----------

@app.on_event("startup")
async def startup():
    """Bootstrap dev environment and start background tasks."""
    if auth_manager.key_count == 0:
        dev_key = "gk-dev-" + "0" * 48
        auth_manager.add_key(
            key=dev_key,
            owner="development",
            tier="premium",
            rpm_limit=1000,
            tpm_limit=10_000_000,
        )
        print(f"  Dev API key created: {dev_key}")

    # Start periodic session cleanup
    asyncio.create_task(_session_cleanup_loop())


async def _session_cleanup_loop():
    """Periodically clean up expired sessions."""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        removed = session_manager.cleanup_expired()
        if removed > 0:
            print(f"  Cleaned up {removed} expired sessions")
