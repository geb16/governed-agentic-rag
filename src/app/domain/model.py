"""Provider-neutral contracts for bounded model interactions."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.domain.contracts import StrictModel


class AgentDraft(StrictModel):
    """Schema returned by the model and validated before it reaches callers."""

    answer: str = Field(min_length=1, max_length=6_000)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=12)
    grounded: bool


class ModelToolCall(StrictModel):
    """Provider-neutral representation of one proposed function call."""

    call_id: str
    name: str
    arguments_json: str


class ModelTurn(StrictModel):
    """Provider-neutral result of one model interaction."""

    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    final: AgentDraft | None = None
    continuation_items: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
