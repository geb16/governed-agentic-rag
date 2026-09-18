"""Prepare blinded review items and accept researcher adjudications.

The module preserves opaque identities and randomized review order across a run,
then validates one condition-blinded researcher's field-level decisions.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 1.3 and Map 3.5.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
    [2] Python Software Foundation, "secrets — Generate secure random numbers
        for managing secrets."
        https://docs.python.org/3/library/secrets.html
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterable, Mapping

from pydantic import Field, model_validator

from paired_agent_evaluation.domain.executions import StrictModel
from paired_agent_evaluation.domain.observations import NormalizedObservation, ObservedRoute
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication

_NEUTRAL_FAILURE_RESPONSE = "The system could not safely produce a response."
RESEARCHER_ADJUDICATOR_ID = "researcher-adjudicator"
_CONDITION_SPECIFIC_FAILURES = frozenset(
    {
        "The model output did not pass baseline safety validation.",
        "I cannot process this request because it conflicts with baseline safety controls.",
        "The governed workflow could not safely produce a response.",
        "The governed workflow could not safely complete the request.",
    }
)
_CONDITION_INDICATOR = re.compile(r"\b(?:baseline|governed)\b", re.IGNORECASE)


class ReviewItem(StrictModel):
    """Represents the condition-neutral evidence shown to a reviewer."""

    blinded_id: str
    query: str
    response: str
    contexts: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    route_review_required: bool
    groundedness_review_required: bool

    @model_validator(mode="after")
    def reject_condition_indicators(self) -> ReviewItem:
        """Fail closed if reviewer-visible text discloses an experiment condition."""
        visible_text = (self.query, self.response, *self.contexts, *self.citation_ids)
        if any(_CONDITION_INDICATOR.search(value) for value in visible_text):
            raise ValueError("review packet contains a condition indicator")
        return self


class BlindingPlan(StrictModel):
    """Persists opaque identities and condition-independent review order."""

    schema_version: int = 1
    assignments: dict[str, str]
    review_order: list[str]

    @model_validator(mode="after")
    def validate_closed_mapping(self) -> BlindingPlan:
        """Validates a complete, one-to-one assignment and review order."""
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
    """Creates opaque identifiers and a randomized order for unique observations.

    Args:
        observation_ids: Stable observation identifiers to blind.

    Returns:
        A validated plan containing one opaque identity per observation.

    Raises:
        ValueError: If an observation identifier occurs more than once.
    """
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
    """Builds a reviewer-visible item when human judgment is required.

    Route review takes precedence over automatic groundedness eligibility. An
    answered observation still requests claim-support review, including when its
    route also requires adjudication.

    Returns:
        A blinded review item, or ``None`` when no review is required.
    """
    grounded = bool(
        observation.answer
        and observation.terminal_error_code is None
        and observation.observed_route not in {ObservedRoute.DENY, ObservedRoute.SAFE_TERMINATE}
    )
    route = observation.route_requires_adjudication
    if not grounded and not route:
        return None
    response = observation.answer or ""
    if response in _CONDITION_SPECIFIC_FAILURES:
        response = _NEUTRAL_FAILURE_RESPONSE
    return ReviewItem(
        blinded_id=blinded_id(observation.key.observation_id, plan=plan),
        query=query,
        response=response,
        contexts=contexts,
        citation_ids=observation.citations,
        route_review_required=route,
        groundedness_review_required=grounded,
    )


def order_review_items(items: Mapping[str, ReviewItem], *, plan: BlindingPlan) -> list[ReviewItem]:
    """Orders available review items according to the persisted random order.

    Raises:
        ValueError: If an item identifies an observation absent from the plan.
    """
    unexpected = set(items) - set(plan.assignments)
    if unexpected:
        raise ValueError(f"Review items are absent from the blinding plan: {sorted(unexpected)}")
    return [
        items[observation_id] for observation_id in plan.review_order if observation_id in items
    ]


def resolve_reviews(reviews: list[Adjudication]) -> dict[str, ResolvedAdjudication]:
    """Validates and indexes one researcher's blinded decisions.

    Every record must use the same researcher identity and each blinded item may
    occur only once. Missing required fields remain pending during scoring.

    Args:
        reviews: Condition-blinded decisions from the researcher-adjudicator.

    Returns:
        Validated decisions keyed by blinded identity.

    Raises:
        ValueError: If multiple researcher identities or duplicate items occur.
    """
    reviewers = {item.reviewer_id for item in reviews}
    if reviewers - {RESEARCHER_ADJUDICATOR_ID}:
        raise ValueError(f"reviewer_id must be {RESEARCHER_ADJUDICATOR_ID!r}")
    resolved: dict[str, ResolvedAdjudication] = {}
    for item in reviews:
        if item.blinded_id in resolved:
            raise ValueError(f"duplicate adjudication for {item.blinded_id}")
        resolved[item.blinded_id] = ResolvedAdjudication(
            blinded_id=item.blinded_id,
            reviewer_id=item.reviewer_id,
            observed_route=item.observed_route,
            claim_support_passed=item.claim_support_passed,
        )
    return resolved


def apply_route_review(
    observation: NormalizedObservation,
    *,
    plan: BlindingPlan,
    resolved: dict[str, ResolvedAdjudication],
) -> NormalizedObservation:
    """Applies a resolved route decision to an observation awaiting review.

    Returns the original observation when route review is unnecessary or remains
    unresolved; otherwise returns a copy marked as researcher-adjudicated.
    """
    if not observation.route_requires_adjudication:
        return observation
    decision = resolved.get(blinded_id(observation.key.observation_id, plan=plan))
    if decision is None or decision.observed_route is None:
        return observation
    return observation.model_copy(
        update={
            "observed_route": decision.observed_route,
            "route_source": "blinded_researcher_adjudication",
            "route_requires_adjudication": False,
        }
    )
