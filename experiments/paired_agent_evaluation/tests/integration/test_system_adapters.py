from pathlib import Path
from typing import Any

from app.evaluation.dataset.enums import ReviewDecision
from app.evaluation.dataset.models import HumanDecision
from app.governance.contracts import ClassificationDraft, GovernedFinalDraft, ProposedActionDraft
from app.governance.llm import ModelResult
from conftest import BaselineAnswerModel, GovernedAnswerModel, StaticRetriever

from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import Condition


def test_both_frozen_systems_run_against_isolated_shared_fixture(
    tmp_path: Path, settings, answer_case
) -> None:
    schedule = build_schedule([answer_case], repetitions=1, seed=20260831)
    by_condition = {item.key.condition: item for item in schedule}
    baseline = BaselineSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: BaselineAnswerModel(),
    ).execute(answer_case, by_condition[Condition.BASELINE], tmp_path / "baseline")
    governed = GovernedSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: GovernedAnswerModel(),
    ).execute(answer_case, by_condition[Condition.GOVERNED], tmp_path / "governed")
    assert baseline.request_accepted is True
    assert governed.request_accepted is True
    assert baseline.request == governed.request
    assert baseline.state_before == governed.state_before
    assert governed.audit_events
    assert normalize(baseline).route_requires_adjudication is True
    assert normalize(governed).observed_route.value == "answer"


class GovernedDualRoleRefundModel:
    pass

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

    execution = GovernedSystemRunner(
        settings,
        retriever_factory=lambda _: StaticRetriever(),
        model_factory=lambda _: GovernedDualRoleRefundModel(),
    ).execute(case, scheduled, tmp_path)

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
