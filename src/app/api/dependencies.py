from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.application.baseline.ports import BaselineUseCase


# function to retrieve the baseline use case from the FastAPI request context
def get_agent(request: Request) -> BaselineUseCase:
    agent: BaselineUseCase | None = request.app.state.agent
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Baseline model is not configured",
        )
    return agent
