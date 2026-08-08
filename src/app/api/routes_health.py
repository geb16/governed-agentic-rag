"""Liveness and dependency-readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

from app.domain.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live(request: Request) -> HealthResponse:
    """Report process liveness without asserting dependency readiness.

    Args:
        request: Active request used to read service metadata.

    Returns:
        An ``ok`` health response when the process can serve HTTP traffic.
    """
    settings = request.app.state.settings
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        status="ok",
        timestamp=datetime.now(UTC),
    )


@router.get("/ready", response_model=HealthResponse)
def ready(request: Request, response: Response) -> HealthResponse:
    """Report whether retrieval and model-backed invocation are configured.

    Args:
        request: Active request used to inspect application state.
        response: Mutable response whose status becomes 503 when dependencies are absent.

    Returns:
        A structured ``ready`` or ``not_ready`` health response.
    """
    settings = request.app.state.settings
    is_ready = request.app.state.agent is not None and request.app.state.retriever is not None
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        status="ready" if is_ready else "not_ready",
        timestamp=datetime.now(UTC),
    )
