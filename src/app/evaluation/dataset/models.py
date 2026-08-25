# Strict, provider-neutral contracts for cases and the frozen scoring rubric.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.support import SyntheticCaseFixture
from app.domain.tasks import TaskRequest
from app.evaluation.dataset.enums import (
    DatasetSplit,
    InteractionChannel,
    RecoveryExpectation,
    ReviewDecision,
    ScenarioCategory,
)


class EvaluationModel(BaseModel):
    """Reject undeclared fields so benchmark drift fails loudly."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HumanDecision(EvaluationModel):
    """Deterministic human input replayed after a required review route."""

    role: str = Field(min_length=2, max_length=100)
    decision: ReviewDecision


class ExpectedRecovery(EvaluationModel):
    """Gold recovery result for a deterministic fault plan."""

    expectation: RecoveryExpectation = RecoveryExpectation.NOT_APPLICABLE
    expected_attempts: int = Field(default=0, ge=0, le=5)
    expected_error_code: str | None = None

    @model_validator(mode="after")
    def validate_recovery_contract(self) -> ExpectedRecovery:
        """Keep attempt and error oracles consistent with the disposition."""
        if self.expectation == RecoveryExpectation.NOT_APPLICABLE:
            if self.expected_attempts or self.expected_error_code:
                raise ValueError("non-failure recovery cannot declare attempts or errors")
        elif self.expectation == RecoveryExpectation.RETRIED_AND_SUCCEEDED:
            if self.expected_attempts < 2 or self.expected_error_code:
                raise ValueError("successful recovery requires retries and no terminal error")
        elif self.expected_attempts < 1 or not self.expected_error_code:
            raise ValueError("safe termination requires attempts and an error code")
        return self


class ExpectedBehavior(EvaluationModel):
    # Common observable oracle, independent of either system architecture.
    ...
class EvaluationCase(EvaluationModel):
    """One isolated synthetic request, environment, and pre-adjudicated oracle."""

    schema_version: Literal[1] = 1
    dataset_version: Literal["1.0.0"] = "1.0.0"
    case_id: str = Field(pattern=r"^case_eval_[0-9]{4}$")
    split: DatasetSplit
    category: ScenarioCategory
    channel: InteractionChannel
    title: str = Field(min_length=5, max_length=160)
    request: TaskRequest
    fixture: SyntheticCaseFixture
    expected: ExpectedBehavior
    label_rationale: str = Field(min_length=20, max_length=500)
    tags: list[str] = Field(min_length=1, max_length=16)
    minimal_pair_id: str | None = Field(default=None, pattern=r"^pair_[a-z0-9_]+$")
    design_source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_identity_and_faults(self) -> EvaluationCase:
        """Bind input and fixture identity and isolate fault cases."""
        if self.request.case_id != self.case_id or self.fixture.case_id != self.case_id:
            raise ValueError("request, fixture, and case identifiers must match")
        has_fault = bool(self.fixture.fault_plans)
        if has_fault != (self.category == ScenarioCategory.TOOL_FAILURE):
            raise ValueError("fault plans are allowed only and required for tool_failure cases")
        return self

