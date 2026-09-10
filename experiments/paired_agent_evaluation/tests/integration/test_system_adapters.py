from pathlib import Path
from typing import Any

from app.evaluation.dataset.enums import ReviewDecision
from app.evaluation.dataset.models import HumanDecision
from app.governance.contracts import ClassificationDraft, GovernedFinalDraft, ProposedActionDraft
from app.governance.llm import ModelResult
from conftest import BaselineAnswerModel, GovernedAnswerModel, StaticRetriever

from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournalStore,
)
from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import Condition
from paired_agent_evaluation.domain.observations import AcceptanceStatus


class MemoryAcceptanceRecorder:
    """Retain acceptance evidence for direct adapter integration tests."""

    def __init__(self) -> None:
        self.accepted = False

    def mark_accepted(self) -> None:
        self.accepted = True


def test_both_frozen_systems_run_against_isolated_shared_fixture(
    tmp_path: Path, settings, answer_case
) -> None:
    schedule = build_schedule([answer_case], repetitions=1, seed=20260831)
    by_condition = {item.key.condition: item for item in schedule}
    attempts = FilesystemAttemptJournalStore(tmp_path / "attempts")
    baseline_attempt = attempts.begin(by_condition[Condition.BASELINE].key.observation_id, 1)
    baseline = BaselineSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: BaselineAnswerModel(),
    ).execute(
        answer_case,
        by_condition[Condition.BASELINE],
        baseline_attempt.workspace,
        acceptance=baseline_attempt,
    )
    governed_attempt = attempts.begin(by_condition[Condition.GOVERNED].key.observation_id, 1)
    governed = GovernedSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: GovernedAnswerModel(),
    ).execute(
        answer_case,
        by_condition[Condition.GOVERNED],
        governed_attempt.workspace,
        acceptance=governed_attempt,
    )
    assert baseline.request_accepted is True
    assert governed.request_accepted is True
    assert baseline.request == governed.request
    assert baseline.state_before == governed.state_before
    assert governed.audit_events
    assert normalize(baseline).route_requires_adjudication is True
    assert normalize(governed).observed_route.value == "answer"


class GovernedDualRoleRefundModel:
    """Deterministically require both finance_manager and fraud_reviewer approval."""

    model_name = "fixed-test-model"

    def classify(self, *_: Any, **__: Any) -> ModelResult[ClassificationDraft]:
        return ModelResult(
            ClassificationDraft(
                intent="refund",
                task_type="state_changing",
                sensitivity="moderate",
                confidence=1.0,
                summary="A large refund was requested.",
            ),
            input_tokens=2,
            output_tokens=1,
        )

    def propose(self, *_: Any, **__: Any) -> ModelResult[ProposedActionDraft]:
        return ModelResult(
            ProposedActionDraft(
                kind="tool",
                tool_name="issue_refund",
                arguments_json=(
                    '{"ticket_id": "TKT-1003", "amount_minor": 500000, "currency": "GBP", '
                    '"idempotency_key": "adapter-test-dual-role-refund"}'
                ),
                confidence=1.0,
                rationale="The evidence supports a large candidate refund.",
            ),
            input_tokens=2,
            output_tokens=1,
        )

    def finalize(self, *_: Any, **__: Any) -> ModelResult[GovernedFinalDraft]:
        return ModelResult(
            GovernedFinalDraft(answer="Completed.", grounded=False),
            input_tokens=2,
            output_tokens=1,
        )


def test_governed_approval_replay_applies_every_available_decision(
    tmp_path: Path, settings, answer_case
) -> None:
    case = answer_case.model_copy(
        update={
            "expected": answer_case.expected.model_copy(
                update={
                    "human_decisions": [
                        HumanDecision(role="fraud_reviewer", decision=ReviewDecision.APPROVE),
                    ]
                }
            )
        }
    )
    schedule = build_schedule([case], repetitions=1, seed=20260831)
    scheduled = next(item for item in schedule if item.key.condition == Condition.GOVERNED)
    attempt = FilesystemAttemptJournalStore(tmp_path / "attempts").begin(
        scheduled.key.observation_id, 1
    )

    execution = GovernedSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: GovernedDualRoleRefundModel(),
    ).execute(case, scheduled, attempt.workspace, acceptance=attempt)

    assert execution.request_accepted is True
    assert execution.initial_response is not None
    assert {item["role"] for item in execution.initial_response["approvals"]} == {
        "finance_manager",
        "fraud_reviewer",
    }
    assert execution.response is not None
    approvals_by_role = {item["role"]: item["status"] for item in execution.response["approvals"]}
    assert approvals_by_role["fraud_reviewer"] == "approved"
    assert approvals_by_role["finance_manager"] == "pending"
    assert execution.response["status"] == "pending_approval"


class UnavailableBaselineModel:
    """Simulate a provider connection failure before any response is accepted."""

    model_name = "unavailable-test-model"

    def complete(self, **_: Any):
        raise ConnectionError("provider unavailable")


class MalformedBaselineModel:
    """Simulate response parsing failure after the provider returned data."""

    model_name = "malformed-test-model"

    def complete(self, **_: Any):
        raise ValueError("provider response violated the structured-output contract")


# Testing if a provider failure before the first response is not accepted by the system runner.
def test_provider_failure_before_first_response_is_not_accepted(
    tmp_path: Path, settings, answer_case
) -> None:
    schedule = build_schedule([answer_case], repetitions=1, seed=20260831)
    scheduled = next(item for item in schedule if item.key.condition == Condition.BASELINE)
    acceptance = MemoryAcceptanceRecorder()

    execution = BaselineSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: UnavailableBaselineModel(),
    ).execute(answer_case, scheduled, tmp_path, acceptance=acceptance)

    assert execution.acceptance == AcceptanceStatus.INVALID
    assert execution.request_accepted is False
    assert acceptance.accepted is False
    assert execution.error_type == "ConnectionError"


# Testing if a provider response that fails parsing after being returned
# is still accepted by the system runner.
def test_response_processing_failure_after_provider_return_is_accepted(
    tmp_path: Path, settings, answer_case
) -> None:
    schedule = build_schedule([answer_case], repetitions=1, seed=20260831)
    scheduled = next(item for item in schedule if item.key.condition == Condition.BASELINE)
    acceptance = MemoryAcceptanceRecorder()

    execution = BaselineSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: MalformedBaselineModel(),
    ).execute(answer_case, scheduled, tmp_path, acceptance=acceptance)

    assert execution.acceptance == AcceptanceStatus.ACCEPTED
    assert execution.request_accepted is True
    assert acceptance.accepted is True
