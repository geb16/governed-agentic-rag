# Create blinded review packets and resolve independent reviewer decisions.

from __future__ import annotations

import hashlib

from pydantic import Field

from paired_agent_evaluation.domain.executions import StrictModel
from paired_agent_evaluation.domain.observations import NormalizedObservation
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication


class ReviewItem(StrictModel):
    blinded_id: str
    query: str
    response: str
    contexts: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    route_review_required: bool
    groundedness_review_required: bool


def blinded_id(observation_id: str, *, run_id: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{observation_id}".encode()).hexdigest()
    return f"blind_{digest[:24]}"


def build_review_item(
    observation: NormalizedObservation,
    *,
    run_id: str,
    query: str,
    contexts: list[str],
) -> ReviewItem | None:
    grounded = bool(observation.answer and not observation.route_requires_adjudication)
    route = observation.route_requires_adjudication
    if not grounded and not route:
        return None
    return ReviewItem(
        blinded_id=blinded_id(observation.key.observation_id, run_id=run_id),
        query=query,
        response=observation.answer or "",
        contexts=contexts,
        citation_ids=observation.citations,
        route_review_required=route,
        groundedness_review_required=bool(observation.answer),
    )


def resolve_reviews(
    reviews: list[Adjudication],
    *,
    resolutions: list[ResolvedAdjudication] | None = None,
) -> dict[str, ResolvedAdjudication]:
    supplied = {item.blinded_id: item for item in resolutions or []}
    grouped: dict[str, list[Adjudication]] = {}
    for review in reviews:
        grouped.setdefault(review.blinded_id, []).append(review)
    resolved: dict[str, ResolvedAdjudication] = {}
    for identity, items in grouped.items():
        reviewers = {item.reviewer_id for item in items}
        if len(reviewers) < 2:
            continue
        routes = {item.observed_route for item in items if item.observed_route is not None}
        claims = {
            item.claim_support_passed for item in items if item.claim_support_passed is not None
        }
        if len(routes) <= 1 and len(claims) <= 1:
            resolved[identity] = ResolvedAdjudication(
                blinded_id=identity,
                observed_route=next(iter(routes), None),
                claim_support_passed=next(iter(claims), None),
                reviewer_count=len(reviewers),
            )
        elif identity in supplied and supplied[identity].disagreement_resolved:
            resolved[identity] = supplied[identity]
    return resolved


def apply_route_review(
    observation: NormalizedObservation,
    *,
    run_id: str,
    resolved: dict[str, ResolvedAdjudication],
) -> NormalizedObservation:
    if not observation.route_requires_adjudication:
        return observation
    decision = resolved.get(blinded_id(observation.key.observation_id, run_id=run_id))
    if decision is None or decision.observed_route is None:
        return observation
    return observation.model_copy(
        update={
            "observed_route": decision.observed_route,
            "route_source": "blinded_dual_review",
            "route_requires_adjudication": False,
        }
    )
