from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.domain.tool import ControlledTool
from app.domain.tool_router import FaultInjector

from app.domain.schemas import (
    RetrievedChunk,
    ToolCallRecord,
    ToolExecutionContext,
)


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
