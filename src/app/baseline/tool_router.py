"""Validate and dispatch model-proposed tool calls through an allowlist.

Rejects unknown tools and invalid JSON arguments, applies deterministic fault
injection, then executes with trusted context. Every path, including denial,
fault, and exception, returns a timed ToolExecution instead of raising.
Core:
    - ToolRouter: ToolGateway implementation exposing strict function specs.
References:
    [1] OpenAI, "Function calling." https://platform.openai.com/docs/guides/function-calling
    [2] OWASP, "Top 10 for LLM Applications."
        https://owasp.org/www-project-top-10-for-large-language-model-applications/
"""

from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.baseline.application.contracts import ToolCallRecord, ToolStatus
from app.baseline.application.ports import ToolExecution
from app.domain.actions import ActionOutcome, ActionProposal, ActionResultStatus
from app.domain.evidence import RetrievedChunk
from app.domain.tasks import ToolExecutionContext
from app.tools.base import ControlledTool
from app.tools.faults import FaultInjector


class ToolRouter:
    """Authorize model proposals through an explicit deterministic allowlist."""

    def __init__(
        self,
        tools: list[ControlledTool[Any]],
        *,
        fault_injector: FaultInjector | None = None,
    ) -> None:
        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise ValueError("Tool names must be unique")
        self._tools = {tool.name: tool for tool in tools}
        self._fault_injector = fault_injector

    @property
    def specs(self) -> list[dict[str, Any]]:
        """Return strict Responses API function definitions for allowlisted tools."""

        return [
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_model.model_json_schema(),
                "strict": True,
            }
            for tool in self._tools.values()
        ]

    def execute(
        self,
        *,
        call_id: str,
        name: str,
        arguments_json: str,
        context: ToolExecutionContext,
    ) -> ToolExecution:
        """Validate, optionally fault, and execute one proposed tool call.

        Args:
            call_id: Provider-assigned call identifier.
            name: Proposed tool name.
            arguments_json: Untrusted JSON arguments emitted by the model.
            context: Trusted case and requester context injected by the application.

        Returns:
            A serializable output and governance-neutral execution record. Invalid,
            unknown, faulted, and exceptional calls are represented as outcomes rather
            than escaping across the application boundary.
        """
        started = perf_counter()
        tool = self._tools.get(name)
        if tool is None:
            return self._denied(
                call_id,
                name,
                {},
                "Tool is not in the allowlist",
                "tool_not_allowlisted",
                context,
                started,
            )

        try:
            parsed_json = json.loads(arguments_json)
            if not isinstance(parsed_json, dict):
                raise ValueError("Tool arguments must be a JSON object")
            arguments = tool.input_model.model_validate(parsed_json)
        except (json.JSONDecodeError, ValidationError, ValueError):
            return self._denied(
                call_id,
                name,
                {},
                "Tool arguments failed validation",
                "tool_arguments_invalid",
                context,
                started,
            )

        proposal = ActionProposal(
            proposal_id=call_id,
            action_type=name,
            arguments=arguments.model_dump(mode="json"),
        )
        if self._fault_injector is not None:
            fault = self._fault_injector.consume(context.case_id, name)
            if fault is not None:
                message = (
                    f"Injected {fault.mode.value} on deterministic attempt {fault.attempt_number}."
                )
                outcome = ActionOutcome(
                    outcome_id=call_id,
                    status=ActionResultStatus.FAILED,
                    case_id=context.case_id,
                    message=message,
                    state_changed=False,
                    error_code=fault.error_code,
                    retryable=fault.retryable,
                )
                record = ToolCallRecord(
                    call_id=call_id,
                    tool_name=name,
                    status=ToolStatus.FAILED,
                    arguments=proposal.arguments,
                    result_summary=message,
                    duration_ms=round((perf_counter() - started) * 1_000, 3),
                    proposal=proposal,
                    outcome=outcome,
                )
                return ToolExecution(
                    json.dumps(
                        {
                            "error": fault.error_code,
                            "failure_mode": fault.mode.value,
                            "retryable": fault.retryable,
                            "attempt_number": fault.attempt_number,
                        },
                        separators=(",", ":"),
                    ),
                    record,
                )

        try:
            result = tool.execute(arguments, context)
            result_json = result.model_dump_json()
            result_data = result.model_dump(mode="json")
            chunks = [
                RetrievedChunk.model_validate(item) for item in result_data.get("matches", [])
            ]
            summary = result_json[:500]
            outcome = ActionOutcome(
                outcome_id=call_id,
                status=result.outcome_status,
                case_id=context.case_id,
                message=result.message,
                state_changed=result.state_changed,
            )
            record = ToolCallRecord(
                call_id=call_id,
                tool_name=name,
                status=ToolStatus.SUCCEEDED,
                arguments=proposal.arguments,
                result_summary=summary,
                duration_ms=round((perf_counter() - started) * 1_000, 3),
                proposal=proposal,
                outcome=outcome,
                evidence=result.evidence,
            )
            return ToolExecution(result_json, record, chunks)
        except Exception:
            outcome = ActionOutcome(
                outcome_id=call_id,
                status=ActionResultStatus.FAILED,
                case_id=context.case_id,
                message="Tool execution failed.",
                state_changed=False,
                error_code="tool_execution_failed",
                retryable=False,
            )
            record = ToolCallRecord(
                call_id=call_id,
                tool_name=name,
                status=ToolStatus.FAILED,
                arguments=proposal.arguments,
                result_summary="Tool execution failed",
                duration_ms=round((perf_counter() - started) * 1_000, 3),
                proposal=proposal,
                outcome=outcome,
            )
            return ToolExecution(
                '{"error":"tool_execution_failed"}',
                record,
            )

    @staticmethod
    def _denied(
        call_id: str,
        name: str,
        arguments: dict[str, Any],
        summary: str,
        error_code: str,
        context: ToolExecutionContext,
        started: float,
    ) -> ToolExecution:

        proposal = ActionProposal(
            proposal_id=call_id,
            action_type=name,
            arguments=arguments,
        )
        outcome = ActionOutcome(
            outcome_id=call_id,
            status=ActionResultStatus.DENIED,
            case_id=context.case_id,
            message=summary,
            state_changed=False,
            error_code=error_code,
            retryable=False,
        )
        record = ToolCallRecord(
            call_id=call_id,
            tool_name=name,
            status=ToolStatus.DENIED,
            arguments=arguments,
            result_summary=summary,
            duration_ms=round((perf_counter() - started) * 1_000, 3),
            proposal=proposal,
            outcome=outcome,
        )
        return ToolExecution(
            json.dumps(
                {"error": error_code, "retryable": False},
                separators=(",", ":"),
            ),
            record,
        )
