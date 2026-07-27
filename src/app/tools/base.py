from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.domain.schemas import ControlledToolResult, ToolExecutionContext

ArgumentsT = TypeVar("ArgumentsT", bound=BaseModel)


class ControlledTool(Protocol[ArgumentsT]):
    name: str
    description: str
    input_model: type[ArgumentsT]

    def execute(
        self,
        arguments: ArgumentsT,
        context: ToolExecutionContext,
    ) -> ControlledToolResult: ...

