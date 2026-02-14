"""
Admin API for Gonka.ai gateway.

Provides administrative endpoints for:
- Usage statistics (global, per-key, per-model, per-session)
- API key management (create, list, revoke)
- Model status and health
- Session management

All admin endpoints require the GONKA_ADMIN_API_KEY.
"""

import time
import uuid

from fastapi import APIRouter, Request

from config.settings import get_settings
from gateway.auth import AuthManager, extract_api_key
from gateway.errors import openai_error
from gateway.metering import UsageMeter
from gateway.router import ModelRouter
from agent.sessions import SessionManager
from agent.tiering import ModelTiering
from serving.health import HealthChecker

router = APIRouter(prefix="/admin", tags=["admin"])

# Set by gateway main.py at startup
_auth_mgr = None
_usage_meter = None
_model_router = None
_session_mgr = None
_tiering = None
_health_checker = None


def init_admin_routes(
    auth_manager: AuthManager,
    usage_meter: UsageMeter,
    model_router: ModelRouter,
    session_manager: SessionManager,
    tiering: ModelTiering,
    health_checker: HealthChecker,
):
    global _auth_mgr, _usage_meter, _model_router, _session_mgr, _tiering, _health_checker
    _auth_mgr = auth_manager
    _usage_meter = usage_meter
    _model_router = model_router
    _session_mgr = session_manager
    _tiering = tiering
    _health_checker = health_checker


def _require_admin(request: Request):
    """Validate admin API key."""
    settings = get_settings()
    api_key = extract_api_key(request)

    if not settings.admin_api_key:
        # No admin key configured — allow dev access
        return True

    if api_key != settings.admin_api_key:
        raise ValueError("Invalid admin API key")
    return True


# ---------- Usage Statistics ----------


@router.get("/usage")
async def global_usage(request: Request, since_hours: float = 24):
    """Get global usage statistics."""
    _require_admin(request)
    since = time.time() - (since_hours * 3600)
    stats = _usage_meter.get_global_stats(since)
    return {"period_hours": since_hours, **stats}


@router.get("/usage/key/{api_key}")
async def key_usage(api_key: str, request: Request, since_hours: float = 24):
    """Get usage statistics for a specific API key."""
    _require_admin(request)
    since = time.time() - (since_hours * 3600)
    usage = _usage_meter.get_usage_by_key(api_key, since)
    breakdown = _usage_meter.get_usage_breakdown(api_key, since)
    return {"api_key": api_key[:8] + "...", "period_hours": since_hours,
            "summary": usage, "by_model": breakdown}


@router.get("/usage/model/{model}")
async def model_usage(model: str, request: Request, since_hours: float = 24):
    """Get usage statistics for a specific model."""
    _require_admin(request)
    since = time.time() - (since_hours * 3600)
    usage = _usage_meter.get_usage_by_model(model, since)
    return {"model": model, "period_hours": since_hours, **usage}


@router.get("/usage/session/{session_id}")
async def session_usage(session_id: str, request: Request):
    """Get usage statistics for a specific agent session."""
    _require_admin(request)
    usage = _usage_meter.get_usage_by_session(session_id)
    return {"session_id": session_id, **usage}


# ---------- API Key Management ----------


@router.get("/keys")
async def list_keys(request: Request):
    """List all API keys (masked)."""
    _require_admin(request)
    keys = _auth_mgr.list_keys()
    return {"keys": keys, "count": len(keys)}


@router.post("/keys")
async def create_key(request: Request):
    """Create a new API key."""
    _require_admin(request)
    body = await request.json()

    owner = body.get("owner", "unknown")
    tier = body.get("tier", "standard")
    rpm_limit = body.get("rpm_limit", 60)
    tpm_limit = body.get("tpm_limit", 100_000)
    key = body.get("key", f"gk-{uuid.uuid4().hex}")

    api_key = _auth_mgr.add_key(key, owner, tier, rpm_limit, tpm_limit)
    return {
        "key": api_key.key,
        "owner": api_key.owner,
        "tier": api_key.tier,
        "rpm_limit": api_key.rpm_limit,
        "tpm_limit": api_key.tpm_limit,
    }


@router.delete("/keys/{api_key}")
async def revoke_key(api_key: str, request: Request):
    """Revoke an API key."""
    _require_admin(request)
    revoked = _auth_mgr.revoke_key(api_key)
    return {"revoked": revoked, "key": api_key[:8] + "..."}


# ---------- Model Status ----------


@router.get("/models")
async def model_status(request: Request):
    """Get detailed model status including health."""
    _require_admin(request)
    models = _model_router.list_models()
    return {"models": models, "count": len(models)}


@router.get("/models/health")
async def models_health(request: Request):
    """Check health of all model backends."""
    _require_admin(request)
    status = await _health_checker.get_status()
    queue = await _health_checker.get_queue_depth()
    return {
        "backend": status.to_dict(),
        "queue": queue,
    }


@router.post("/models/reload")
async def reload_models(request: Request):
    """Reload model configuration from models.yaml."""
    _require_admin(request)
    _model_router.reload()
    _tiering.reload()
    return {"reloaded": True, "model_count": _model_router.model_count}


# ---------- Sessions ----------


@router.get("/sessions")
async def list_all_sessions(request: Request):
    """List all active sessions (admin view)."""
    _require_admin(request)
    sessions = _session_mgr.list_sessions()
    return {"sessions": sessions, "active_count": _session_mgr.active_count}


@router.post("/sessions/cleanup")
async def force_cleanup(request: Request):
    """Force cleanup of expired sessions."""
    _require_admin(request)
    removed = _session_mgr.cleanup_expired()
    return {"removed": removed, "remaining": _session_mgr.active_count}


# ---------- Tiering ----------


@router.get("/tiering")
async def tiering_config(request: Request):
    """Get current model tiering configuration."""
    _require_admin(request)
    return _tiering.config
