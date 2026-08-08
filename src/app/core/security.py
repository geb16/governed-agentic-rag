"""HTTP authentication, response hardening, and pseudonymous model identifiers."""

import hashlib
import hmac
import secrets
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from starlette.responses import Response

from app.core.config import Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    request: Request,
    supplied_key: str | None = Depends(api_key_header),
) -> None:
    """Enforce constant-time API-key authentication when configured.

    Development and test profiles may operate without a key. Production fails closed
    when configuration is missing and rejects absent or incorrect credentials.

    Args:
        request: Active request containing validated settings.
        supplied_key: Optional credential extracted from ``X-API-Key``.

    Raises:
        HTTPException: If production lacks a key or the supplied key is invalid.
    """
    settings: Settings = request.app.state.settings
    configured = settings.api_key
    if configured is None or not configured.get_secret_value():
        if settings.environment == "production":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return
    if supplied_key is None or not secrets.compare_digest(
        supplied_key, configured.get_secret_value()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credential",
            headers={"WWW-Authenticate": "ApiKey"},
        )


def stable_safety_identifier(requester_id: str, secret: str) -> str:
    """Create a keyed pseudonymous identifier; never send raw enterprise identity upstream."""

    return hmac.new(
        secret.encode("utf-8"),
        requester_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def security_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Apply declared-size checks and defensive response headers.

    Args:
        request: Incoming HTTP request.
        call_next: Downstream ASGI request handler.

    Returns:
        A 400/413 rejection or the downstream response with security headers.

    Note:
        ``Content-Length`` is an early rejection control, not a streaming-body limit.
        The deployment proxy must independently enforce maximum body size.
    """
    settings: Settings = request.app.state.settings
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_bytes:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        except ValueError:
            return Response(status_code=status.HTTP_400_BAD_REQUEST)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response
