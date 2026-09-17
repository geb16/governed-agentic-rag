"""Verify blinded review ordering and independent adjudication resolution."""

from __future__ import annotations

import secrets

import pytest
from pydantic import ValidationError

from paired_agent_evaluation.application.adjudication import (
    BlindingPlan,
    ReviewItem,
    build_review_item,
    create_blinding_plan,
    order_review_items,
    resolve_reviews,
)
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    NormalizedObservation,
    ObservedRoute,
)
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication


class _ReverseRandom:
    """Provide deterministic reverse ordering at the randomness boundary."""

    def shuffle(self, values: list[str]) -> None:
        values.reverse()


def _observation(
    *,
    answer: str,
    route: ObservedRoute | None,
    route_review_required: bool = False,
    terminal_error_code: str | None = None,
) -> NormalizedObservation:
    """Build a minimal accepted observation for reviewer-projection tests."""
    return NormalizedObservation(
        key=ExecutionKey(
            case_id="case_eval_0001",
            repetition=1,
            condition=Condition.GOVERNED,
        ),
        acceptance=AcceptanceStatus.ACCEPTED,
        observed_route=route,
        route_requires_adjudication=route_review_required,
        answer=answer,
        terminal_error_code=terminal_error_code,
        latency_ms=1,
        input_tokens=1,
        output_tokens=1,
        raw_sha256="a" * 64,
    )


def _plan(observation: NormalizedObservation) -> BlindingPlan:
    observation_id = observation.key.observation_id
    return BlindingPlan(
        assignments={observation_id: f"blind_{'1' * 32}"},
        review_order=[observation_id],
    )


def test_blinding_plan_uses_random_opaque_ids_and_an_independent_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assign opaque tokens and randomize review order independently of identity."""
    tokens = iter(("1" * 32, "2" * 32))
    monkeypatch.setattr(secrets, "token_hex", lambda _: next(tokens))
    monkeypatch.setattr(secrets, "SystemRandom", _ReverseRandom)
    observation_ids = ["case_eval_0001__r1__baseline", "case_eval_0001__r1__governed"]

    plan = create_blinding_plan(observation_ids)

    assert plan.assignments == {
        observation_ids[0]: f"blind_{'1' * 32}",
        observation_ids[1]: f"blind_{'2' * 32}",
    }
    assert plan.review_order == observation_ids[::-1]


def test_review_packet_follows_private_plan_order() -> None:
    """Order reviewer-visible items using only the persisted private plan."""
    first = "case_eval_0001__r1__baseline"
    second = "case_eval_0001__r1__governed"
    plan = BlindingPlan(
        assignments={first: f"blind_{'1' * 32}", second: f"blind_{'2' * 32}"},
        review_order=[second, first],
    )
    items = {
        first: ReviewItem(
            blinded_id=plan.identity_for(first),
            query="First",
            response="First response",
            route_review_required=False,
            groundedness_review_required=True,
        ),
        second: ReviewItem(
            blinded_id=plan.identity_for(second),
            query="Second",
            response="Second response",
            route_review_required=False,
            groundedness_review_required=True,
        ),
    }

    ordered = order_review_items(items, plan=plan)

    assert [item.blinded_id for item in ordered] == [
        plan.identity_for(second),
        plan.identity_for(first),
    ]


def test_review_projection_neutralizes_condition_specific_terminal_wording() -> None:
    """Keep route review blinded without mutating the normalized observation."""
    original = "The governed workflow could not safely produce a response."
    observation = _observation(
        answer=original,
        route=None,
        route_review_required=True,
        terminal_error_code="missing_citation",
    )

    item = build_review_item(
        observation,
        plan=_plan(observation),
        query="Help with this request.",
        contexts=[],
    )

    assert item is not None
    assert item.response == "The system could not safely produce a response."
    assert item.route_review_required is True
    assert item.groundedness_review_required is False
    assert observation.answer == original


@pytest.mark.parametrize("route", [ObservedRoute.DENY, ObservedRoute.SAFE_TERMINATE])
def test_terminal_or_safety_failure_does_not_request_groundedness(
    route: ObservedRoute,
) -> None:
    """Exclude terminal fallback text when no separate route decision is needed."""
    observation = _observation(
        answer="The model output did not pass baseline safety validation.",
        route=route,
    )

    assert (
        build_review_item(
            observation,
            plan=_plan(observation),
            query="Help with this request.",
            contexts=[],
        )
        is None
    )


@pytest.mark.parametrize("indicator", ["baseline", "governed", "GOVERNED"])
def test_review_packet_rejects_condition_indicators(indicator: str) -> None:
    """Fail closed when any reviewer-facing text can reveal the condition."""
    with pytest.raises(ValidationError, match="condition indicator"):
        ReviewItem(
            blinded_id=f"blind_{'1' * 32}",
            query="Help with this request.",
            response=f"The {indicator} system returned a response.",
            route_review_required=False,
            groundedness_review_required=True,
        )


def test_two_independent_matching_reviews_resolve() -> None:
    """Resolve a field when two distinct reviewers submit the same decision."""
    reviews = [
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r1",
            observed_route=ObservedRoute.ANSWER,
        ),
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r2",
            observed_route=ObservedRoute.ANSWER,
        ),
    ]

    assert resolve_reviews(reviews)["blind_1"].observed_route == ObservedRoute.ANSWER


def test_reviewers_must_independently_decide_each_resolved_field() -> None:
    """Different single-reviewer fields do not constitute dual review."""
    reviews = [
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r1",
            observed_route=ObservedRoute.ANSWER,
        ),
        Adjudication(blinded_id="blind_1", reviewer_id="r2", claim_support_passed=True),
    ]

    assert resolve_reviews(reviews) == {}


def test_independently_dual_reviewed_fields_resolve_together() -> None:
    """Combine fields independently supported by different reviewer pairs."""
    reviews = [
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r1",
            observed_route=ObservedRoute.ANSWER,
        ),
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r2",
            observed_route=ObservedRoute.ANSWER,
            claim_support_passed=True,
        ),
        Adjudication(blinded_id="blind_1", reviewer_id="r3", claim_support_passed=True),
    ]

    decision = resolve_reviews(reviews)["blind_1"]

    assert decision.observed_route == ObservedRoute.ANSWER
    assert decision.claim_support_passed is True
    assert decision.reviewer_count == 3


def test_disagreement_requires_explicit_resolution() -> None:
    """Leave disagreement unresolved until an explicit resolution is supplied."""
    reviews = [
        Adjudication(blinded_id="blind_1", reviewer_id="r1", claim_support_passed=True),
        Adjudication(blinded_id="blind_1", reviewer_id="r2", claim_support_passed=False),
    ]

    assert resolve_reviews(reviews) == {}

    resolution = ResolvedAdjudication(
        blinded_id="blind_1",
        claim_support_passed=False,
        reviewer_count=2,
        disagreement_resolved=True,
        resolution_notes="Unsupported material claim.",
    )

    assert resolve_reviews(reviews, resolutions=[resolution])["blind_1"] == resolution
