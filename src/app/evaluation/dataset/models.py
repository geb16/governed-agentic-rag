# Strict, provider-neutral contracts for cases and the frozen scoring rubric.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.evaluation.dataset.enums import ReviewDecision


class EvaluationModel(BaseModel):
    """Reject undeclared fields so benchmark drift fails loudly."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HumanDecision(EvaluationModel):
    """Deterministic human input replayed after a required review route."""

    role: str = Field(min_length=2, max_length=100)
    decision: ReviewDecision

