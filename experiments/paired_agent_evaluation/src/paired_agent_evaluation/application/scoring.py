# Apply the frozen Phase-5 metric definitions to normalized observations.

from __future__ import annotations

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
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
   
    
    route_pending_reason = "blinded route adjudication is unresolved" if route_pending else None
    contributions = [
        _metric(
            observation,
            "appropriate_route_rate",
            eligible=True,
            passed=(observed is not None and observed.value == expected.value),
            pending=route_pending_reason,
        ),
    ]
    return [
        item.model_copy(update={"numerator": 0.0, "denominator": 0.0})
        if item.pending_reason
        else item
        for item in contributions
    ]
