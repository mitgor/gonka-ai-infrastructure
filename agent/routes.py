"""
Agent API Routes for Gonka.ai gateway.

Adds agent-specific endpoints on top of the OpenAI-compatible API:
- POST /v1/sessions — create/manage sessions
- GET/POST/DELETE /v1/memory — long-term context storage
- POST /v1/webhooks — register async callbacks

These endpoints are accessed via the same API key auth as chat completions.
"""

import uuid
import time
from typing import Optional

from fastapi import APIRouter, Request

from gateway.auth import AuthManager, extract_api_key
from gateway.errors import openai_error
from agent.sessions import SessionManager
from agent.memory import MemoryStore
from agent.webhooks import WebhookManager

router = APIRouter(prefix="/v1", tags=["agent"])


# These are set by the gateway main.py at startup
_session_mgr: Optional[SessionManager] = None
_memory_store: Optional[MemoryStore] = None
_webhook_mgr: Optional[WebhookManager] = None
_auth_mgr: Optional[AuthManager] = None


def init_agent_routes(
    session_manager: SessionManager,
    memory_store: MemoryStore,
    webhook_manager: WebhookManager,
    auth_manager: AuthManager,
):
    """Initialize agent routes with shared managers."""
    global _session_mgr, _memory_store, _webhook_mgr, _auth_mgr
    _session_mgr = session_manager
    _memory_store = memory_store
    _webhook_mgr = webhook_manager
    _auth_mgr = auth_manager


def _validate_key(request: Request):
    api_key_str = extract_api_key(request)
    api_key = _auth_mgr.validate(api_key_str)
    if not api_key:
        raise ValueError("Invalid API key")
    return api_key_str, api_key


# ---------- Sessions ----------


@router.get("/sessions")
async def list_sessions(request: Request):
    """List active sessions for the authenticated API key."""
    api_key_str, _ = _validate_key(request)
    sessions = _session_mgr.list_sessions(api_key=api_key_str)
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions")
async def create_session(request: Request):
    """Create a new session with optional metadata."""
    api_key_str, _ = _validate_key(request)
    body = await request.json() if await request.body() else {}

    session_id = body.get("session_id", f"sess-{uuid.uuid4().hex[:16]}")
    session = _session_mgr.get_or_create(session_id, api_key_str)

    if body.get("metadata"):
        session.metadata.update(body["metadata"])

    if body.get("system_message"):
        _session_mgr.append_messages(session_id, [
            {"role": "system", "content": body["system_message"]}
        ])

    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "metadata": session.metadata,
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request):
    """Get session details and history."""
    api_key_str, _ = _validate_key(request)
    session = _session_mgr.get(session_id)
    if not session:
        return openai_error(404, f"Session '{session_id}' not found", "invalid_request_error", "not_found")

    return {
        "session_id": session.session_id,
        "message_count": session.message_count,
        "messages": session.messages,
        "created_at": session.created_at,
        "last_accessed": session.last_accessed,
        "metadata": session.metadata,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Delete a session."""
    _validate_key(request)
    deleted = _session_mgr.delete(session_id)
    return {"deleted": deleted, "session_id": session_id}


# ---------- Memory ----------


@router.get("/memory/keys")
async def list_memory_keys(request: Request, namespace: str = "default"):
    """List all memory keys in a namespace."""
    api_key_str, _ = _validate_key(request)
    keys = _memory_store.list_keys(api_key_str, namespace)
    return {"keys": keys, "namespace": namespace, "count": len(keys)}


@router.get("/memory/namespaces")
async def list_namespaces(request: Request):
    """List all memory namespaces."""
    api_key_str, _ = _validate_key(request)
    namespaces = _memory_store.list_namespaces(api_key_str)
    return {"namespaces": namespaces}


@router.post("/memory")
async def put_memory(request: Request):
    """Store a memory entry."""
    api_key_str, _ = _validate_key(request)
    body = await request.json()

    key = body.get("key")
    value = body.get("value")
    if not key or not value:
        return openai_error(400, "Both 'key' and 'value' are required", "invalid_request_error", "bad_request")

    namespace = body.get("namespace", "default")
    metadata = body.get("metadata", "{}")
    if isinstance(metadata, dict):
        import json
        metadata = json.dumps(metadata)

    _memory_store.put(api_key_str, key, value, namespace, metadata)
    return {"stored": True, "key": key, "namespace": namespace}


@router.get("/memory/{key}")
async def get_memory(key: str, request: Request, namespace: str = "default"):
    """Get a memory entry by key."""
    api_key_str, _ = _validate_key(request)
    entry = _memory_store.get(api_key_str, key, namespace)
    if not entry:
        return openai_error(404, f"Memory key '{key}' not found", "invalid_request_error", "not_found")

    return {
        "key": entry.key,
        "value": entry.value,
        "namespace": entry.namespace,
        "metadata": entry.metadata,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.delete("/memory/{key}")
async def delete_memory(key: str, request: Request, namespace: str = "default"):
    """Delete a memory entry."""
    api_key_str, _ = _validate_key(request)
    deleted = _memory_store.delete(api_key_str, key, namespace)
    return {"deleted": deleted, "key": key}


@router.post("/memory/search")
async def search_memory(request: Request):
    """Search memory entries using semantic similarity."""
    api_key_str, _ = _validate_key(request)
    body = await request.json()

    query = body.get("query", "")
    namespace = body.get("namespace", "default")
    limit = body.get("limit", 10)

    results = _memory_store.search(api_key_str, query, namespace, limit)
    return {"results": results, "query": query, "namespace": namespace}


# ---------- Webhooks ----------


@router.post("/webhooks")
async def register_webhook(request: Request):
    """Register a webhook URL for async notifications."""
    api_key_str, _ = _validate_key(request)
    body = await request.json()

    url = body.get("url")
    if not url:
        return openai_error(400, "'url' is required", "invalid_request_error", "bad_request")

    webhook_id = body.get("webhook_id", f"wh-{uuid.uuid4().hex[:12]}")
    session_id = body.get("session_id")
    max_retries = body.get("max_retries", 3)

    reg = _webhook_mgr.register(webhook_id, api_key_str, url, session_id, max_retries)
    return {
        "webhook_id": reg.webhook_id,
        "url": reg.url,
        "session_id": reg.session_id,
        "created_at": reg.created_at,
    }


@router.get("/webhooks")
async def list_webhooks(request: Request):
    """List registered webhooks."""
    api_key_str, _ = _validate_key(request)
    webhooks = _webhook_mgr.list_webhooks(api_key_str)
    return {"webhooks": webhooks, "count": len(webhooks)}


@router.get("/webhooks/{webhook_id}")
async def webhook_status(webhook_id: str, request: Request):
    """Get webhook delivery status."""
    _validate_key(request)
    status = _webhook_mgr.get_status(webhook_id)
    if not status:
        return openai_error(404, f"Webhook '{webhook_id}' not found", "invalid_request_error", "not_found")
    return status


@router.delete("/webhooks/{webhook_id}")
async def unregister_webhook(webhook_id: str, request: Request):
    """Unregister a webhook."""
    _validate_key(request)
    removed = _webhook_mgr.unregister(webhook_id)
    return {"removed": removed, "webhook_id": webhook_id}
