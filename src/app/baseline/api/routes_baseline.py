"""Expose the authenticated endpoint for baseline agent invocations.

POST /baseline/invoke requires an API key, validates the body as
BaselineRequest, and runs the synchronous use case in a threadpool so
blocking model and tool I/O never stalls the event loop.
Core:
    - router: APIRouter mounted under /baseline.
    - invoke_baseline: handler returning a structured BaselineResponse.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from app.baseline.api.dependencies import get_agent
from app.baseline.application.contracts import BaselineRequest, BaselineResponse
from app.baseline.application.ports import BaselineUseCase
from app.core.security import require_api_key

router = APIRouter(
    prefix="/baseline",
    tags=["baseline"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/invoke", response_model=BaselineResponse)
async def invoke_baseline(
    request: BaselineRequest,
    agent: Annotated[BaselineUseCase, Depends(get_agent)],
) -> BaselineResponse:
    """Run one validated baseline request outside the asynchronous event loop.

    Args:
        request: Strict task request parsed from the HTTP body.
        agent: Baseline use case resolved from application state.

    Returns:
        The structured baseline outcome, including safety and evidence metadata.
    """
    return await run_in_threadpool(agent.invoke, request)
