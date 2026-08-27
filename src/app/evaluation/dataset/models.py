# Strict, provider-neutral contracts for cases and the frozen scoring rubric.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.support import SyntheticCaseFixture
from app.domain.tasks import TaskRequest
from app.evaluation.dataset.enums import (
    DatasetSplit,
    ExpectedRiskLevel,
    ExpectedRoute,
    ExpectedSensitivity,
    ExpectedTaskType,
    InteractionChannel,
    RecoveryExpectation,
    ReviewDecision,
    ScenarioCategory,
    TraceFact,
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
    """Common observable oracle, independent of either system architecture."""

    route: ExpectedRoute
    intent: str = Field(min_length=2, max_length=100)
    task_type: ExpectedTaskType
    sensitivity: ExpectedSensitivity
    risk_level: ExpectedRiskLevel
    expected_tool: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    state_change_expected: bool = False
    approval_roles: list[str] = Field(default_factory=list)
    human_decisions: list[HumanDecision] = Field(default_factory=list)
    clarification_fields: list[str] = Field(default_factory=list)
    denial_reason_code: str | None = None
    retrieval_documents: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recovery: ExpectedRecovery = Field(default_factory=ExpectedRecovery)
    required_trace_facts: list[TraceFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_route_contract(self) -> ExpectedBehavior:
        """Enforce coherent labels before an evaluator can consume them."""
        if self.route == ExpectedRoute.HUMAN_REVIEW and not self.approval_roles:
            raise ValueError("human_review routes require approval_roles")
        if self.route != ExpectedRoute.HUMAN_REVIEW and self.human_decisions:
            raise ValueError("human decisions are valid only for human_review routes")
        decision_roles = [item.role for item in self.human_decisions]
        if decision_roles and (
            len(decision_roles) != len(set(decision_roles))
            or set(decision_roles) != set(self.approval_roles)
        ):
            raise ValueError("human decisions must cover each required role exactly once")
        if self.route == ExpectedRoute.CLARIFY and not self.clarification_fields:
            raise ValueError("clarify routes require clarification_fields")
        if self.route == ExpectedRoute.DENY and not self.denial_reason_code:
            raise ValueError("deny routes require denial_reason_code")
        if self.route in {ExpectedRoute.EXECUTE, ExpectedRoute.SAFE_TERMINATE}:
            if self.expected_tool is None:
                raise ValueError("execute and safe_terminate routes require expected_tool")
        if self.route in {ExpectedRoute.CLARIFY, ExpectedRoute.DENY}:
            if self.expected_tool is not None or self.state_change_expected:
                raise ValueError("clarify and deny routes cannot authorize a state change")
        if self.route == ExpectedRoute.SAFE_TERMINATE and self.state_change_expected:
            raise ValueError("safe termination cannot authorize a state change")
        if self.expected_tool is None and self.tool_arguments:
            raise ValueError("tool_arguments require expected_tool")
        return self


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
        if has_fault and self.expected.recovery.expectation == RecoveryExpectation.NOT_APPLICABLE:
            raise ValueError("tool_failure cases require a recovery expectation")
        if (
            not has_fault
            and self.expected.recovery.expectation != RecoveryExpectation.NOT_APPLICABLE
        ):
            raise ValueError("non-failure cases cannot declare recovery behavior")
        return self


class MetricDefinition(EvaluationModel):
    """Machine-readable metric definition frozen before execution."""

    metric_id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    description: str = Field(min_length=10)
    eligible_when: str = Field(min_length=3)
    numerator: str = Field(min_length=3)
    denominator: str = Field(min_length=3)
    direction: Literal["higher_is_better", "lower_is_better"]
    failure_policy: str = Field(min_length=10)


class ScoringRubric(EvaluationModel):
    """Frozen evaluation rules shared by baseline and governed conditions."""

    schema_version: Literal[1] = 1
    rubric_version: Literal["1.0.0"] = "1.0.0"
    dataset_version: Literal["1.0.0"] = "1.0.0"
    unit_of_analysis: str
    repetitions_per_case: int = Field(ge=1, le=10)
    common_harness_requirements: list[str] = Field(min_length=1)
    invalid_run_policy: str
    metrics: list[MetricDefinition] = Field(min_length=1)
    reporting_requirements: list[str] = Field(min_length=1)
    composite_score: None = None
