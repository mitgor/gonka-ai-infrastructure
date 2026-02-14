"""
OpenAI-compatible error responses for Gonka.ai gateway.

All errors follow the OpenAI error format:
{
    "error": {
        "message": "...",
        "type": "...",
        "code": "..."
    }
}
"""

from fastapi import Request
from fastapi.responses import JSONResponse


def openai_error(status_code: int, message: str, error_type: str, code: str) -> JSONResponse:
    """Create an OpenAI-format error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "code": code,
            }
        },
    )


def bad_request(message: str) -> JSONResponse:
    return openai_error(400, message, "invalid_request_error", "bad_request")


def unauthorized(message: str = "Invalid API key") -> JSONResponse:
    return openai_error(401, message, "invalid_request_error", "invalid_api_key")


def not_found(message: str) -> JSONResponse:
    return openai_error(404, message, "invalid_request_error", "not_found")


def rate_limited(message: str, retry_after: int = 60) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "message": message,
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
            }
        },
        headers={"Retry-After": str(retry_after)},
    )


def server_error(message: str = "Internal server error") -> JSONResponse:
    return openai_error(500, message, "server_error", "internal_error")


def backend_unavailable(model: str) -> JSONResponse:
    return openai_error(
        503,
        f"Model backend '{model}' is currently unavailable. Please retry.",
        "server_error",
        "backend_unavailable",
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler that returns OpenAI-format errors."""
    return server_error(str(exc))
