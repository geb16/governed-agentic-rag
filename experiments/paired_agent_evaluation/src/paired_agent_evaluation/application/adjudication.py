"""Create opaque review identities and resolve independent reviewer decisions."""

from __future__ import annotations

import re
import secrets
from collections.abc import Hashable, Iterable, Mapping
from typing import TypeVar

from pydantic import Field, model_validator

from paired_agent_evaluation.domain.executions import StrictModel
from paired_agent_evaluation.domain.observations import NormalizedObservation
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication

DecisionT = TypeVar("DecisionT", bound=Hashable)


class ReviewItem(StrictModel):
    blinded_id: str
    query: str
    response: str
    contexts: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    route_review_required: bool
    groundedness_review_required: bool


class BlindingPlan(StrictModel):
    """Persist opaque identities and reviewer order without exposing conditions."""

    schema_version: int = 1
    assignments: dict[str, str]
    review_order: list[str]

    @model_validator(mode="after")
    def validate_closed_mapping(self) -> BlindingPlan:
        """Require one unique opaque identity and one order entry per observation."""
        observation_ids = set(self.assignments)
        if not observation_ids or observation_ids != set(self.review_order):
            raise ValueError("blinding assignments and review order must contain the same IDs")
        if len(self.review_order) != len(observation_ids):
            raise ValueError("review order must contain every observation exactly once")
        blinded_ids = list(self.assignments.values())
        if len(blinded_ids) != len(set(blinded_ids)):
            raise ValueError("blinded identities must be unique")
        if any(re.fullmatch(r"blind_[a-f0-9]{32}", value) is None for value in blinded_ids):
            raise ValueError("blinded identities must be opaque 128-bit hexadecimal tokens")
        return self

    def identity_for(self, observation_id: str) -> str:
        """Return the persisted opaque identity for an observation."""
        try:
            return self.assignments[observation_id]
        except KeyError as error:
            raise ValueError(
                f"Observation is absent from the blinding plan: {observation_id}"
            ) from error


def create_blinding_plan(observation_ids: Iterable[str]) -> BlindingPlan:
    """Create a cryptographically random mapping and independent review order."""
    identities = list(observation_ids)
    if len(identities) != len(set(identities)):
        raise ValueError("observation identities must be unique")
    assignments: dict[str, str] = {}
    issued: set[str] = set()
    for observation_id in identities:
        blinded = f"blind_{secrets.token_hex(16)}"
        while blinded in issued:
            blinded = f"blind_{secrets.token_hex(16)}"
        assignments[observation_id] = blinded
        issued.add(blinded)
    review_order = identities.copy()
    secrets.SystemRandom().shuffle(review_order)
    return BlindingPlan(assignments=assignments, review_order=review_order)


def blinded_id(observation_id: str, *, plan: BlindingPlan) -> str:
    """Resolve an observation through the private, persisted blinding plan."""
    return plan.identity_for(observation_id)


def build_review_item(
    observation: NormalizedObservation,
    *,
    plan: BlindingPlan,
    query: str,
    contexts: list[str],
) -> ReviewItem | None:
    grounded = bool(observation.answer and not observation.route_requires_adjudication)
    route = observation.route_requires_adjudication
    if not grounded and not route:
        return None
    return ReviewItem(
        blinded_id=blinded_id(observation.key.observation_id, plan=plan),
        query=query,
        response=observation.answer or "",
        contexts=contexts,
        citation_ids=observation.citations,
        route_review_required=route,
        groundedness_review_required=bool(observation.answer),
    )


def order_review_items(items: Mapping[str, ReviewItem], *, plan: BlindingPlan) -> list[ReviewItem]:
    """Order reviewer-visible items by the plan's random, condition-independent order."""
    unexpected = set(items) - set(plan.assignments)
    if unexpected:
        raise ValueError(f"Review items are absent from the blinding plan: {sorted(unexpected)}")
    return [
        items[observation_id] for observation_id in plan.review_order if observation_id in items
    ]


def _resolve_field(
    decisions: Iterable[tuple[str, DecisionT | None]],
    *,
    resolution: DecisionT | None,
) -> tuple[DecisionT | None, set[str], bool]:
    """Resolve one field only when at least two distinct reviewers decided it."""
    provided = [(reviewer, value) for reviewer, value in decisions if value is not None]
    reviewers = {reviewer for reviewer, _ in provided}
    if len(reviewers) < 2:
        return None, set(), False
    values = {value for _, value in provided}
    if len(values) == 1:
        return next(iter(values)), reviewers, False
    if resolution is not None:
        return resolution, reviewers, True
    return None, set(), False


def resolve_reviews(
    reviews: list[Adjudication],
    *,
    resolutions: list[ResolvedAdjudication] | None = None,
) -> dict[str, ResolvedAdjudication]:
    """Resolve route and claim-support fields from independent dual reviews."""
    supplied = {item.blinded_id: item for item in resolutions or []}
    grouped: dict[str, list[Adjudication]] = {}
    for review in reviews:
        grouped.setdefault(review.blinded_id, []).append(review)
    resolved: dict[str, ResolvedAdjudication] = {}
    for identity, items in grouped.items():
        supplied_resolution = supplied.get(identity)
        usable_resolution = (
            supplied_resolution
            if supplied_resolution is not None and supplied_resolution.disagreement_resolved
            else None
        )
        route, route_reviewers, route_resolved = _resolve_field(
            ((item.reviewer_id, item.observed_route) for item in items),
            resolution=usable_resolution.observed_route if usable_resolution else None,
        )
        claim, claim_reviewers, claim_resolved = _resolve_field(
            ((item.reviewer_id, item.claim_support_passed) for item in items),
            resolution=usable_resolution.claim_support_passed if usable_resolution else None,
        )
        reviewers = route_reviewers | claim_reviewers
        if not reviewers:
            continue
        resolved[identity] = ResolvedAdjudication(
            blinded_id=identity,
            observed_route=route,
            claim_support_passed=claim,
            reviewer_count=len(reviewers),
            disagreement_resolved=route_resolved or claim_resolved,
            resolution_notes=(
                usable_resolution.resolution_notes
                if usable_resolution and (route_resolved or claim_resolved)
                else ""
            ),
        )
    return resolved


def apply_route_review(
    observation: NormalizedObservation,
    *,
    plan: BlindingPlan,
    resolved: dict[str, ResolvedAdjudication],
) -> NormalizedObservation:
    if not observation.route_requires_adjudication:
        return observation
    decision = resolved.get(blinded_id(observation.key.observation_id, plan=plan))
    if decision is None or decision.observed_route is None:
        return observation
    return observation.model_copy(
        update={
            "observed_route": decision.observed_route,
            "route_source": "blinded_dual_review",
            "route_requires_adjudication": False,
        }
    )
