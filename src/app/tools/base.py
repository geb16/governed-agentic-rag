"""Structural contract implemented by every allowlisted controlled tool."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.domain.actions import ControlledToolResult
from app.domain.tasks import ToolExecutionContext

ArgumentsT = TypeVar("ArgumentsT", bound=BaseModel)


class ControlledTool(Protocol[ArgumentsT]):
    """Expose strict arguments and governance-neutral execution results."""

    name: str
    description: str
    input_model: type[ArgumentsT]

    def execute(
        self,
        arguments: ArgumentsT,
        context: ToolExecutionContext,
    ) -> ControlledToolResult:
        """Execute validated arguments within application-injected trusted context."""
        ...
