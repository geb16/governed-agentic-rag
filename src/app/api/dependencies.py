from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.baseline.agent import BaselineAgent


# function to retrieve the BaselineAgent instance from the FastAPI request context
def get_agent(request: Request) -> BaselineAgent:
    agent: BaselineAgent | None = request.app.state.agent
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Baseline model is not configured",
        )
    return agent
