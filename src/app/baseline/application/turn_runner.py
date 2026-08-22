"""Bounded baseline model loop and controlled-tool dispatch."""

from __future__ import annotations

import logging

from app.baseline.application.contracts import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    SafetyResult,
)
from app.baseline.application.policy import AgentRuntimePolicy
from app.baseline.application.ports import ModelGateway, OutputSafetyPolicy, ToolGateway
from app.baseline.application.prompts import SYSTEM_PROMPT
from app.baseline.application.responses import BaselineResponseFactory
from app.baseline.application.state import InvocationState
from app.core.logging import log_execution
from app.core.security import stable_safety_identifier
from app.domain.events import ExecutionEvent
from app.domain.model import ModelTurn
from app.domain.tasks import ToolExecutionContext

logger = logging.getLogger(__name__)


class BaselineTurnRunner:
    """Run bounded model turns and dispatch controlled tool proposals."""

    def __init__(
        self,
        *,
        policy: AgentRuntimePolicy,
        model: ModelGateway,
        tool_gateway: ToolGateway,
        output_guardrail: OutputSafetyPolicy,
        responses: BaselineResponseFactory,
    ) -> None:
        self._policy = policy
        self._model = model
        self._tool_gateway = tool_gateway
        self._output_guardrail = output_guardrail
        self._responses = responses

    def run(
        self,
        request: BaselineRequest,
        trace_id: str,
        state: InvocationState,
    ) -> BaselineResponse:
        """Run model turns until a validated terminal response is available.

        Args:
            request: Normalized task and trusted case identifiers.
            trace_id: Per-invocation operational trace identifier.
            state: Request-local conversation and evidence state.

        Returns:
            A completed response, a safety refusal, or a bounded failure response.
        """
        for turn_index in range(1, self._policy.max_agent_turns + 1):
            turn = self._model.complete(
                input_items=state.input_items,
                instructions=SYSTEM_PROMPT,
                tools=self._tool_gateway.specs,
                safety_identifier=stable_safety_identifier(
                    request.requester_id,
                    self._policy.safety_identifier_secret,
                ),
            )
            state.record_model_turn(turn)
            self._log(
                ExecutionEvent.MODEL_TURN_COMPLETED,
                request,
                trace_id,
                turn=turn_index,
                proposed_tool_calls=len(turn.tool_calls),
                has_final=turn.final is not None,
            )

            invalid_category = self._invalid_turn_category(turn, state)
            if invalid_category is not None:
                return self.blocked(request, trace_id, state, invalid_category)

            if turn.tool_calls:
                self._execute_tool(request, trace_id, state, turn)
                continue
            if turn.final is None:
                return self.failed(request, trace_id, state)

            decision = self._output_guardrail.inspect(
                turn.final,
                allowed_chunk_ids=set(state.available_chunks),
            )
            if decision.blocked:
                return self.blocked(
                    request,
                    trace_id,
                    state,
                    decision.category or "output_guardrail",
                )
            return self._responses.create(
                request=request,
                trace_id=trace_id,
                status=AgentStatus.COMPLETED,
                answer=turn.final.answer,
                citations=state.citations_for(turn.final.cited_chunk_ids),
                evidence=state.evidence_for(turn.final.cited_chunk_ids),
                tool_calls=state.tool_calls,
                usage=state.usage,
                safety=SafetyResult(blocked=False),
            )
        return self.failed(request, trace_id, state)

    def _invalid_turn_category(
        self,
        turn: ModelTurn,
        state: InvocationState,
    ) -> str | None:
        if len(turn.tool_calls) > 1 or (turn.tool_calls and turn.final is not None):
            return "invalid_model_turn"
        if turn.tool_calls and len(state.tool_calls) >= self._policy.max_tool_calls:
            return "tool_call_limit"
        return None

    def _execute_tool(
        self,
        request: BaselineRequest,
        trace_id: str,
        state: InvocationState,
        turn: ModelTurn,
    ) -> None:
        call = turn.tool_calls[0]
        execution = self._tool_gateway.execute(
            call_id=call.call_id,
            name=call.name,
            arguments_json=call.arguments_json,
            context=ToolExecutionContext(
                case_id=request.case_id,
                request_id=request.request_id,
                requester_id=request.requester_id,
            ),
        )
        state.record_tool_execution(turn, execution)
        self._log(
            ExecutionEvent.TOOL_EXECUTED,
            request,
            trace_id,
            tool_name=call.name,
            tool_status=execution.record.status,
            duration_ms=execution.record.duration_ms,
        )

    def blocked(
        self,
        request: BaselineRequest,
        trace_id: str,
        state: InvocationState,
        category: str,
    ) -> BaselineResponse:
        """Create and log a safety refusal for an invalid model output."""
        self._log(
            ExecutionEvent.OUTPUT_BLOCKED,
            request,
            trace_id,
            category=category,
        )
        return self._responses.create(
            request=request,
            trace_id=trace_id,
            status=AgentStatus.REFUSED,
            answer="The model output did not pass baseline safety validation.",
            tool_calls=state.tool_calls,
            usage=state.usage,
            safety=SafetyResult(blocked=True, category=category),
        )

    def failed(
        self,
        request: BaselineRequest,
        trace_id: str,
        state: InvocationState,
    ) -> BaselineResponse:
        """Create a stable failure response without claiming task completion."""
        return self._responses.create(
            request=request,
            trace_id=trace_id,
            status=AgentStatus.FAILED,
            answer="The baseline could not complete the request.",
            tool_calls=state.tool_calls,
            usage=state.usage,
            safety=SafetyResult(blocked=False),
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
