from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.scoring import score_observation
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    ObservedRoute,
)


def _case(paths, case_id):
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    return next(case for case in cases if case.case_id == case_id)


def _metrics(case, observation, reviews=None):
    return {
        item.metric_id: item
        for item in score_observation(
            case,
            observation,
            run_id="run_test",
            adjudications=reviews or {},
        )
    }


def test_governed_human_review_scores_approval_and_unsafe_prevention(paths) -> None:
    case = _case(paths, "case_eval_0044")
    observation = NormalizedObservation(
        key=ExecutionKey(case_id=case.case_id, repetition=1, condition=Condition.GOVERNED),
        acceptance=AcceptanceStatus.ACCEPTED,
        observed_route=ObservedRoute.HUMAN_REVIEW,
        approval_roles=["iam_administrator"],
        approval_decisions=[{"role": "iam_administrator", "status": "approved"}],
        business_state_changed=True,
        latency_ms=1,
        input_tokens=1,
        output_tokens=1,
        raw_sha256="b" * 64,
    )
    metrics = _metrics(case, observation)
    assert metrics["appropriate_route_rate"].numerator == 1
    assert metrics["approval_control_accuracy"].numerator == 1
    assert metrics["unsafe_action_prevention_rate"].numerator == 1
