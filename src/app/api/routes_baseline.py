from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_agent
from app.baseline.agent import BaselineAgent
from app.core.security import require_api_key
from app.domain.schemas import BaselineRequest, BaselineResponse

# Router for the baseline agent endpoints
router = APIRouter(
    prefix="/baseline",
    tags=["baseline"],
    dependencies=[Depends(require_api_key)],
)

# Endpoint to invoke the baseline agent with a request
@router.post("/invoke", response_model=BaselineResponse)
async def invoke_baseline(
    request: BaselineRequest,
    agent: Annotated[BaselineAgent, Depends(get_agent)],
) -> BaselineResponse:
    return await run_in_threadpool(agent.invoke, request)
