# Create blinded review packets and resolve independent reviewer decisions.

from __future__ import annotations

import hashlib

from pydantic import Field

from paired_agent_evaluation.domain.executions import StrictModel
from paired_agent_evaluation.domain.observations import NormalizedObservation


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
