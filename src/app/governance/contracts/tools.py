"""Define provider-neutral tool metadata exposed to governance model ports.

These contracts describe only allowlisted capabilities and strict JSON schemas;
they do not expose dispatch functions or infrastructure implementations.
"""

from typing import Any

from pydantic import Field

from app.domain.contracts import StrictModel


class ToolDefinition(StrictModel):
    """Describe an allowlisted capability and its strict parameter schema.

    The model may use this metadata to propose an action, but only the tool catalog
    can validate the proposal and only the bounded router can execute it.
    """

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1_000)
    parameters: dict[str, Any]
