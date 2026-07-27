from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.rag.retriever import Retriever

from app.baseline.guardrails import InputGuardrail, OutputGuardrail
from app.baseline.model import AgentModel
from app.baseline.prompts import SYSTEM_PROMPT, build_user_prompt
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.logging import log_execution
from app.core.security import stable_safety_identifier
from app.domain.events import ExecutionEvent
from app.domain.schemas import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    EvidenceReference,
    EvidenceType,
    RetrievedChunk,
    SafetyResult,
    ToolCallRecord,
    ToolExecutionContext,
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

        normalized_request = request.model_copy(update={"query": decision.normalized_text})
        chunks = self.retriever.retrieve(normalized_request.query)
        available: dict[str, RetrievedChunk] = {chunk.chunk_id: chunk for chunk in chunks}
        available_evidence: dict[str, EvidenceReference] = {
            chunk.chunk_id: EvidenceReference(
                evidence_id=chunk.chunk_id,
                evidence_type=EvidenceType.KNOWLEDGE_CHUNK,
                source_id=chunk.document_id,
                title=chunk.title,
                content_sha256=chunk.content_sha256,
                score=chunk.score,
            )
            for chunk in chunks
        }

        log_execution(
            logger,
            ExecutionEvent.RETRIEVAL_COMPLETED,
            trace_id=trace_id,
            request_id=request.request_id,
            backend=self.retriever.backend_name,
            result_count=len(chunks),
        )
        input_items: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": build_user_prompt(normalized_request, chunks),
            }
        ]
        tool_records: list[ToolCallRecord] = []
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            for turn_index in range(1, self.settings.max_agent_turns + 1):
                turn = self.model.complete(
                    input_items=input_items,
                    instructions=SYSTEM_PROMPT,
                    tools=self.tool_router.specs,
                    safety_identifier=stable_safety_identifier(
                        request.requester_id,
                        (
                            self.settings.api_key.get_secret_value()
                            if self.settings.api_key is not None
                            else "phase3-development-only"
                        ),
                    ),
                )
                total_input_tokens += turn.input_tokens
                total_output_tokens += turn.output_tokens
                log_execution(
                    logger,
                    ExecutionEvent.MODEL_TURN_COMPLETED,
                    trace_id=trace_id,
                    request_id=request.request_id,
                    turn=turn_index,
                    proposed_tool_calls=len(turn.tool_calls),
                    has_final=turn.final is not None,
                )

                if len(turn.tool_calls) > 1 or (turn.tool_calls and turn.final is not None):
                    return self._blocked_model_output(
                        request,
                        trace_id,
                        tool_records,
                        total_input_tokens,
                        total_output_tokens,
                        "invalid_model_turn",
                    )

                if turn.tool_calls:
                    if len(tool_records) >= self.settings.max_tool_calls:
                        return self._blocked_model_output(
                            request,
                            trace_id,
                            tool_records,
                            total_input_tokens,
                            total_output_tokens,
                            "tool_call_limit",
                        )

                    call = turn.tool_calls[0]
                    execution = self.tool_router.execute(
                        call_id=call.call_id,
                        name=call.name,
                        arguments_json=call.arguments_json,
                        context=ToolExecutionContext(
                            case_id=request.case_id,
                            request_id=request.request_id,
                            requester_id=request.requester_id,
                        ),
                    )

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
            return self._failed(
                request,
                trace_id,
                tool_records,
                total_input_tokens,
                total_output_tokens,
            )     