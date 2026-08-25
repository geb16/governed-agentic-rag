# Strict, provider-neutral contracts for cases and the frozen scoring rubric.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.dataset.enums import (
    RecoveryExpectation,
    ReviewDecision,
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

