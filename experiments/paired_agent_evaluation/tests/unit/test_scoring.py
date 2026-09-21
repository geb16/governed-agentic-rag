"""Verify metric eligibility and outcomes for canonical observations."""

from __future__ import annotations

from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.application.adjudication import BlindingPlan, blinded_id
from paired_agent_evaluation.application.scoring import score_observation
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    ObservedRoute,
)
from paired_agent_evaluation.domain.scores import MetricContribution, ResolvedAdjudication


def _case(paths: EvaluationPaths, case_id: str) -> EvaluationCase:
    """Load one validation case by its stable identifier."""
    cases = EvaluationDataset(paths.repository).cases(DatasetSplit.VALIDATION)
    return next(case for case in cases if case.case_id == case_id)


def _blinding_plan(observation: NormalizedObservation) -> BlindingPlan:
    """Create a valid single-observation blinding plan."""
    observation_id = observation.key.observation_id
    return BlindingPlan(
        assignments={observation_id: f"blind_{'a' * 32}"},
        review_order=[observation_id],
    )


def _metrics(
    case: EvaluationCase,
    observation: NormalizedObservation,
    reviews: dict[str, ResolvedAdjudication] | None = None,
    *,
    plan: BlindingPlan | None = None,
) -> dict[str, MetricContribution]:
    """Score an observation and index its contributions by metric."""
    return {
        item.metric_id: item
        for item in score_observation(
            case,
            observation,
            blinding_plan=plan or _blinding_plan(observation),
            adjudications=reviews or {},
        )
    }


def test_groundedness_requires_membership_and_human_claim_support(
    paths: EvaluationPaths,
) -> None:
    """Keep groundedness pending until eligible citations pass human review."""
    case = _case(paths, "case_eval_0002")
    observation = NormalizedObservation(
        key=ExecutionKey(case_id=case.case_id, repetition=1, condition=Condition.BASELINE),
        acceptance=AcceptanceStatus.ACCEPTED,
        observed_route=ObservedRoute.ANSWER,
        answer="Supported answer",
        citations=["relevant"],
        citation_membership_valid=True,
        retrieved_chunk_documents={"relevant": "refund_policy", "noise": "support_sop"},
        latency_ms=1,
        input_tokens=1,
        output_tokens=1,
        raw_sha256="a" * 64,
    )
    plan = _blinding_plan(observation)
    pending = _metrics(case, observation, plan=plan)
    assert pending["groundedness_rate"].pending_reason is not None
    identity = blinded_id(observation.key.observation_id, plan=plan)
    reviews = {
        identity: ResolvedAdjudication(
            blinded_id=identity,
            reviewer_id="researcher-adjudicator",
            claim_support_passed=True,
        )
    }
    scored = _metrics(case, observation, reviews, plan=plan)
    assert scored["groundedness_rate"].numerator == 1
    assert scored["context_precision"].numerator == 1
    assert scored["context_precision"].denominator == 2


def test_terminal_failure_is_ineligible_for_groundedness(paths: EvaluationPaths) -> None:
    """Do not leave terminal missing-citation outcomes pending human review."""
    case = _case(paths, "case_eval_0002")
    observation = NormalizedObservation(
        key=ExecutionKey(case_id=case.case_id, repetition=1, condition=Condition.GOVERNED),
        acceptance=AcceptanceStatus.ACCEPTED,
        observed_route=ObservedRoute.ANSWER,
        answer="The system could not safely produce a response.",
        terminal_error_code="missing_citation",
        latency_ms=1,
        input_tokens=1,
        output_tokens=1,
        raw_sha256="c" * 64,
    )

    groundedness = _metrics(case, observation)["groundedness_rate"]

    assert groundedness.eligible is False
    assert groundedness.pending_reason is None


def test_governed_human_review_scores_approval_and_unsafe_prevention(
    paths: EvaluationPaths,
) -> None:
    """Credit approved human routing and prevention of direct unsafe action."""
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
