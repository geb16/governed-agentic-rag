"""FastAPI dependency resolvers for application-layer ports."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.baseline.application.ports import BaselineUseCase


def get_agent(request: Request) -> BaselineUseCase:
    """Resolve the configured baseline use case for an HTTP request.

    Args:
        request: Active FastAPI request containing application lifespan state.

    Returns:
        The application-facing baseline invocation port.

    Raises:
        HTTPException: If no model-backed baseline use case is configured.
    """
    agent: BaselineUseCase | None = request.app.state.agent
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Baseline model is not configured",
        )
    return agent
