"""Expose tool metadata and validate proposals without granting execution authority.

The catalog is the boundary between untrusted model proposals and trusted typed
arguments. It exposes only allowlisted schemas, rejects duplicate capability names,
and never dispatches a tool; execution remains in the shared bounded router.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.governance.contracts import (
    ProposedAction,
    ProposedActionDraft,
    ProposedActionKind,
    ToolDefinition,
)
from app.tools.base import ControlledTool


class ToolCatalog:
    """Publish allowlisted metadata and validate candidate tool arguments.

    Args:
        tools: Shared controlled tools eligible for governed proposals.

    Raises:
        ValueError: If two tools declare the same public name.
    """

    def __init__(self, tools: list[ControlledTool[Any]]) -> None:
        """Initialize catalog indexes after rejecting duplicate tool names."""
        names = [tool.name for tool in tools]
        if len(names) != len(set(names)):
            raise ValueError("Tool names must be unique")
        self._tools = {tool.name: tool for tool in tools}

    @property
    def definitions(self) -> list[ToolDefinition]:
        """Return provider-neutral metadata for the model proposal boundary.

        Returns:
            Ordered tool names, descriptions, and strict input-model JSON schemas.
            No executable function or infrastructure object is exposed.
        """
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.input_model.model_json_schema(),
            )
            for tool in self._tools.values()
        ]

    def validate(self, draft: ProposedActionDraft) -> ProposedAction:
        """Convert an untrusted draft into an explicitly validated proposal.

        Args:
            draft: Structured model output whose name and JSON arguments are untrusted.

        Returns:
            A proposal containing normalized typed arguments, or a stable validation
            error for risk policy. Invalid input is data, not an execution exception.
        """
        if draft.kind == ProposedActionKind.RESPOND:
            if draft.tool_name is not None:
                return ProposedAction(
                    **draft.model_dump(),
                    validation_error="response_proposal_must_not_name_tool",
                )
            return ProposedAction(**draft.model_dump())
        if not draft.tool_name or draft.tool_name not in self._tools:
            return ProposedAction(
                **draft.model_dump(),
                validation_error="tool_not_allowlisted",
            )
        try:
            decoded = json.loads(draft.arguments_json)
            if not isinstance(decoded, dict):
                raise ValueError("arguments must be an object")
            validated = self._tools[draft.tool_name].input_model.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError, ValueError):
            return ProposedAction(
                **draft.model_dump(),
                validation_error="tool_arguments_invalid",
            )
        return ProposedAction(
            **draft.model_dump(),
            validated_arguments=validated.model_dump(mode="json"),
        )
