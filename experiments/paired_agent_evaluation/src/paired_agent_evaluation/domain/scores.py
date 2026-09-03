# Metric contributions, estimates, and human adjudication contracts.

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, model_validator

from paired_agent_evaluation.domain.executions import ExecutionKey, StrictModel
from paired_agent_evaluation.domain.observations import ObservedRoute


class Adjudication(StrictModel):
    schema_version: int = 1
    blinded_id: str
    reviewer_id: str
    observed_route: ObservedRoute | None = None
    claim_support_passed: bool | None = None
    notes: str = Field(default="", max_length=2000)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def require_a_decision(self) -> Adjudication:
        if self.observed_route is None and self.claim_support_passed is None:
            raise ValueError("an adjudication must contain at least one decision")
        return self


class ResolvedAdjudication(StrictModel):
    blinded_id: str
    observed_route: ObservedRoute | None = None
    claim_support_passed: bool | None = None
    reviewer_count: int = Field(ge=2)
    disagreement_resolved: bool = False
    resolution_notes: str = ""
