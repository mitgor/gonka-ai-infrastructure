"""
Shared test fixtures for Gonka.ai integration tests.

Uses a mock vLLM backend (FastAPI) to avoid needing real GPU hardware.
"""

import asyncio
import json
import time
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# ---------- Mock vLLM Backend ----------


def create_mock_vllm_app() -> FastAPI:
    """Create a mock vLLM server that returns canned responses."""
    mock_app = FastAPI()

    @mock_app.get("/health")
    async def health():
        return {"status": "ok"}

    @mock_app.get("/v1/models")
    async def models():
        return {
            "object": "list",
            "data": [
                {
                    "id": "moonshotai/Kimi-K2.5",
                    "object": "model",
                    "created": 0,
                    "owned_by": "moonshotai",
                }
            ],
        }

    @mock_app.post("/v1/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        tools = body.get("tools")

        last_msg = messages[-1].get("content", "") if messages else ""

        if stream:
            return _stream_response(last_msg, tools)

        # Tool calling response
        if tools:
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", "moonshotai/Kimi-K2.5"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": f"call_{uuid.uuid4().hex[:8]}",
                                    "type": "function",
                                    "function": {
                                        "name": tools[0]["function"]["name"],
                                        "arguments": json.dumps({"query": last_msg}),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            }

        # Standard response
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "moonshotai/Kimi-K2.5"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock K2.5 response to: {last_msg[:100]}",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }

    def _stream_response(user_msg: str, tools):
        chunks = [
            f"Mock streaming response to: {user_msg[:50]}",
        ]

        async def generate():
            chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            for i, chunk_text in enumerate(chunks):
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "moonshotai/Kimi-K2.5",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                await asyncio.sleep(0.01)

            # Final chunk with usage
            final = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "moonshotai/Kimi-K2.5",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @mock_app.get("/metrics")
    async def metrics():
        return "vllm:num_requests_waiting 0\nvllm:num_requests_running 1\n"

    return mock_app


# ---------- Test Client ----------

DEV_API_KEY = "gk-dev-" + "0" * 48


@pytest.fixture
def gateway_base_url():
    """Base URL for the Gonka gateway."""
    return "http://localhost:9000"


@pytest.fixture
def api_key():
    """Development API key."""
    return DEV_API_KEY


@pytest.fixture
def auth_headers(api_key):
    """Headers with auth for API requests."""
    return {"Authorization": f"Bearer {api_key}"}
