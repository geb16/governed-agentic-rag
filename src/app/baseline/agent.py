from __future__ import annotations

import logging
from uuid import uuid4

from app.rag.retriever import Retriever

from app.baseline.guardrails import InputGuardrail, OutputGuardrail
from app.baseline.model import AgentModel
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.logging import log_execution
from app.domain.events import ExecutionEvent
from app.domain.schemas import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    SafetyResult,
)
from app.persistence.repository import SyntheticRepository

logger = logging.getLogger(__name__)


# BaselineAgent  orchestrates the RAG process, including retrieval, model interaction, 
# tool execution, and guardrail enforcement.
class BaselineAgent:

    def __init__(
        self,
        *,
        settings: Settings,
        retriever: Retriever,
        model: AgentModel,
        tool_router: ToolRouter,
        repository: SyntheticRepository,
        input_guardrail: InputGuardrail | None = None,
        output_guardrail: OutputGuardrail | None = None,
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.model = model
        self.tool_router = tool_router
        self.repository = repository
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.output_guardrail = output_guardrail or OutputGuardrail()

    def invoke(self, request: BaselineRequest) -> BaselineResponse:
        trace_id = f"trace_{uuid4().hex}"
        
        log_execution(
            logger,
            ExecutionEvent.REQUEST_RECEIVED,
            trace_id=trace_id,
            request_id=request.request_id,
        )
        if not self.repository.case_exists(request.case_id):
            return self._response(
                request=request,
                trace_id=trace_id,
                status=AgentStatus.FAILED,
                answer="The requested synthetic evaluation case does not exist.",
                safety=SafetyResult(blocked=False),
                error_code="synthetic_case_not_found",
            )

        decision = self.input_guardrail.inspect(
            request.query,
            max_chars=self.settings.max_query_chars,
        )
        if decision.blocked:
            log_execution(
                logger,
                ExecutionEvent.INPUT_BLOCKED,
                trace_id=trace_id,
                request_id=request.request_id,
                category=decision.category,
            )
            return self._response(
                request=request,
                trace_id=trace_id,
                status=AgentStatus.REFUSED,
                answer=(
                    "I cannot process this request because it conflicts with "
                    "baseline safety controls."
                ),
                safety=SafetyResult(blocked=True, category=decision.category),
            )