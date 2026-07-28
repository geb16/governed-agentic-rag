import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings

# API key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Function to require an API key for access to certain endpoints
def require_api_key(
    request: Request,
    supplied_key: str | None = Depends(api_key_header),
) -> None:
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
