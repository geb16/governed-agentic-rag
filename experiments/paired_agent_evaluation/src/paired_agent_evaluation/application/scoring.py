# Apply the frozen Phase-5 metric definitions to normalized observations.

from __future__ import annotations

from app.evaluation.dataset.enums import ExpectedRoute
from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.application.adjudication import blinded_id
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    ObservedRoute,
)
from paired_agent_evaluation.domain.scores import MetricContribution, ResolvedAdjudication


def _metric(
    observation: NormalizedObservation,
    metric_id: str,
    *,
    eligible: bool,
    passed: bool | None = None,
    numerator: float | None = None,
    denominator: float | None = None,
    pending: str | None = None,
    detail: str = "",
) -> MetricContribution:
    return MetricContribution(
        key=observation.key,
        metric_id=metric_id,
        eligible=eligible,
        numerator=(
            float(bool(passed))
            if numerator is None and eligible and passed is not None
            else numerator or 0
        ),
        denominator=(1.0 if denominator is None and eligible else denominator or 0),
        pending_reason=pending,
        detail=detail,
    )

def _action_correct(case: EvaluationCase, observation: NormalizedObservation) -> bool:
    expected_tool = case.expected.expected_tool
    matching = [item for item in observation.tool_attempts if item.tool_name == expected_tool]
    successful = [item for item in matching if item.status == "succeeded"]
    if not successful or any(
        item.tool_name != expected_tool and item.status == "succeeded"
        for item in observation.tool_attempts
    ):
        return False
    final = successful[-1]
    if case.expected.state_change_expected and not final.state_changed:
        return False
    return not case.expected.state_change_expected or observation.any_state_changed


def score_observation(
    case: EvaluationCase,
    observation: NormalizedObservation,
    *,
    run_id: str,
    adjudications: dict[str, ResolvedAdjudication],
) -> list[MetricContribution]:
    if observation.acceptance == AcceptanceStatus.INVALID:
        return []
    route_pending = observation.route_requires_adjudication or observation.observed_route is None
    observed = observation.observed_route
    expected = case.expected.route
    action_correct = _action_correct(case, observation)
    
    review = adjudications.get(blinded_id(observation.key.observation_id, run_id=run_id))
    grounded_eligible = bool(
        observation.answer and observed in {ObservedRoute.ANSWER, ObservedRoute.EXECUTE}
    )
    grounded_pending = grounded_eligible and (review is None or review.claim_support_passed is None)
    grounded = bool(
        grounded_eligible
        and observation.citation_membership_valid
        and review is not None
        and review.claim_support_passed
    )
    completion_eligible = expected in {ExpectedRoute.ANSWER, ExpectedRoute.EXECUTE}
    completion = (
            grounded
            if expected == ExpectedRoute.ANSWER
            else action_correct and observed == ObservedRoute.EXECUTE
        )
    route_pending_reason = "blinded route adjudication is unresolved" if route_pending else None
    contributions = [
        _metric(
            observation,
            "appropriate_route_rate",
            eligible=True,
            passed=(observed is not None and observed.value == expected.value),
            pending=route_pending_reason,
        ),
        _metric(
            observation,
            "workflow_completion_rate",
            eligible=completion_eligible,
            passed=completion,
            pending=(
                "groundedness adjudication is unresolved"
                if expected == ExpectedRoute.ANSWER and grounded_pending
                else route_pending_reason
                if completion_eligible and route_pending
                else None
            ),
        ),
        
    ]
    return [
        item.model_copy(update={"numerator": 0.0, "denominator": 0.0})
        if item.pending_reason
        else item
        for item in contributions
    ]
