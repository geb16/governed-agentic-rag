from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.domain.schemas import (
    ActionOutcome,
    ActionProposal,
    ActionResultStatus,
    RetrievedChunk,
    ToolCallRecord,
    ToolExecutionContext,
    ToolStatus,
)
from app.tools.base import ControlledTool
from app.tools.faults import FaultInjector


# ToolEXecution dataclass to hold the output of a tool execution,
# the record of the tool call, and any retrieved chunks.
@dataclass(slots=True)
class ToolExecution:
    output_json: str
    record: ToolCallRecord
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)


class ToolRouter:
    """
    Allowlist dispatcher. The model proposes calls;
    And deterministic code authorizes them.
    """

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

    def execute(
        self,
        *,
        call_id: str,
        name: str,
        arguments_json: str,
        context: ToolExecutionContext,
    ) -> ToolExecution:
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
                    f"Injected {fault.mode.value} on deterministic attempt "
                    f"{fault.attempt_number}."
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