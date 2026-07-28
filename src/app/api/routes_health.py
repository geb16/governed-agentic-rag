from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status

from app.domain.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


# check if the service is live and responding
@router.get("/live", response_model=HealthResponse)
def live(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        status="ok",
        timestamp=datetime.now(UTC),
    )


#  ready endpoint checks if the service is ready to handle requests
@router.get("/ready", response_model=HealthResponse)
def ready(request: Request, response: Response) -> HealthResponse:
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
