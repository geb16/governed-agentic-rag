"""Application service coordinating validation, retrieval, and bounded turns."""

from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from app.baseline.application.contracts import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    SafetyResult,
)
from app.baseline.application.policy import AgentRuntimePolicy
from app.baseline.application.ports import (
    CaseReader,
    InputSafetyPolicy,
    ModelGateway,
    OutputSafetyPolicy,
    RetrievalGateway,
    ToolGateway,
)
from app.baseline.application.prompts import build_user_prompt
from app.baseline.application.responses import BaselineResponseFactory
from app.baseline.application.state import InvocationState
from app.baseline.application.turn_runner import BaselineTurnRunner
from app.core.logging import log_execution
from app.domain.events import ExecutionEvent

logger = logging.getLogger(__name__)


class BaselineAgentService:
    """Orchestrate one bounded baseline-agent invocation through application ports."""

    def __init__(
        self,
        *,
        policy: AgentRuntimePolicy,
        retriever: RetrievalGateway,
        model: ModelGateway,
        tool_gateway: ToolGateway,
        case_reader: CaseReader,
        input_guardrail: InputSafetyPolicy,
        output_guardrail: OutputSafetyPolicy,
    ) -> None:
        self._policy = policy
        self._retriever = retriever
        self._case_reader = case_reader
        self._input_guardrail = input_guardrail
        self._responses = BaselineResponseFactory(
            retrieval_backend=retriever.backend_name,
            model_name=model.model_name,
        )
        self._turn_runner = BaselineTurnRunner(
            policy=policy,
            model=model,
            tool_gateway=tool_gateway,
            output_guardrail=output_guardrail,
            responses=self._responses,
        )

    def invoke(self, request: BaselineRequest) -> BaselineResponse:
        """Execute one isolated baseline invocation.

        The method validates trusted case context and user input, retrieves evidence,
        delegates the bounded model/tool loop, and converts unexpected failures into a
        stable response. It does not retain invocation state between calls.

        Args:
            request: Strict task request accepted by the application boundary.

        Returns:
            A completed, refused, or failed baseline response.
        """
        trace_id = f"trace_{uuid4().hex}"
        started = perf_counter()
        self._log(ExecutionEvent.REQUEST_RECEIVED, request, trace_id)

        normalized_query, early_response = self._validate_request(request, trace_id)
        if early_response is not None:
            return early_response

        assert normalized_query is not None
        normalized_request, state = self._prepare_invocation(
            request,
            trace_id,
            normalized_query,
        )
        try:
            response = self._turn_runner.run(normalized_request, trace_id, state)
        except Exception:
            logger.exception(
                "Baseline invocation failed",
                extra={
                    "context": {
                        "event": ExecutionEvent.REQUEST_FAILED,
                        "trace_id": trace_id,
                        "request_id": request.request_id,
                    }
                },
            )
            response = self._turn_runner.failed(request, trace_id, state)

        if response.status == AgentStatus.COMPLETED:
            self._log(
                ExecutionEvent.REQUEST_COMPLETED,
                request,
                trace_id,
                status=response.status,
                duration_ms=round((perf_counter() - started) * 1_000, 3),
                tool_call_count=len(state.tool_calls),
            )
        return response

    def _validate_request(
        self,
        request: BaselineRequest,
        trace_id: str,
    ) -> tuple[str | None, BaselineResponse | None]:
        if not self._case_reader.case_exists(request.case_id):
            return (
                None,
                self._responses.create(
                    request=request,
                    trace_id=trace_id,
                    status=AgentStatus.FAILED,
                    answer="The requested synthetic evaluation case does not exist.",
                    safety=SafetyResult(blocked=False),
                    error_code="synthetic_case_not_found",
                ),
            )

        decision = self._input_guardrail.inspect(
            request.query,
            max_chars=self._policy.max_query_chars,
        )
        if not decision.blocked:
            return decision.normalized_text, None
        self._log(
            ExecutionEvent.INPUT_BLOCKED,
            request,
            trace_id,
            category=decision.category,
        )
        return (
            None,
            self._responses.create(
                request=request,
                trace_id=trace_id,
                status=AgentStatus.REFUSED,
                answer=(
                    "I cannot process this request because it conflicts with "
                    "baseline safety controls."
                ),
                safety=SafetyResult(blocked=True, category=decision.category),
            ),
        )

    def _prepare_invocation(
        self,
        request: BaselineRequest,
        trace_id: str,
        normalized_query: str,
    ) -> tuple[BaselineRequest, InvocationState]:
        normalized_request = request.model_copy(update={"query": normalized_query})
        chunks = self._retriever.retrieve(normalized_request.query)
        self._log(
            ExecutionEvent.RETRIEVAL_COMPLETED,
            request,
            trace_id,
            backend=self._retriever.backend_name,
            result_count=len(chunks),
        )
        return normalized_request, InvocationState.from_retrieval(
            user_prompt=build_user_prompt(normalized_request, chunks),
            chunks=chunks,
        )

    @staticmethod
    def _log(
        event: ExecutionEvent,
        request: BaselineRequest,
        trace_id: str,
        **context: object,
    ) -> None:
        log_execution(
            logger,
            event,
            trace_id=trace_id,
            request_id=request.request_id,
            **context,
        )
