import paired_agent_evaluation.application.adjudication as adjudication_module
from paired_agent_evaluation.application.adjudication import (
    ReviewItem,
    create_blinding_plan,
    order_review_items,
    resolve_reviews,
)
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication


class _ReverseRandom:
    def shuffle(self, values: list[str]) -> None:
        values.reverse()


def test_blinding_plan_uses_random_opaque_ids_and_an_independent_order(monkeypatch) -> None:
    tokens = iter(("1" * 32, "2" * 32))
    monkeypatch.setattr(adjudication_module.secrets, "token_hex", lambda _: next(tokens))
    monkeypatch.setattr(adjudication_module.secrets, "SystemRandom", _ReverseRandom)
    observation_ids = ["case_eval_0001__r1__baseline", "case_eval_0001__r1__governed"]

    plan = create_blinding_plan(observation_ids)

    assert plan.assignments == {
        observation_ids[0]: f"blind_{'1' * 32}",
        observation_ids[1]: f"blind_{'2' * 32}",
    }
    assert plan.review_order == observation_ids[::-1]


def test_review_packet_follows_private_plan_order() -> None:
    first = "case_eval_0001__r1__baseline"
    second = "case_eval_0001__r1__governed"
    plan = adjudication_module.BlindingPlan(
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


# Testing that two independent reviews with the same blinded_id and the same
# observed_route value resolve to that value.
def test_two_independent_matching_reviews_resolve() -> None:
    reviews = [
        Adjudication(blinded_id="blind_1", reviewer_id="r1", observed_route="answer"),
        Adjudication(blinded_id="blind_1", reviewer_id="r2", observed_route="answer"),
    ]
    assert resolve_reviews(reviews)["blind_1"].observed_route.value == "answer"


def test_reviewers_must_independently_decide_each_resolved_field() -> None:
    """Different single-reviewer fields do not constitute dual review."""
    reviews = [
        Adjudication(blinded_id="blind_1", reviewer_id="r1", observed_route="answer"),
        Adjudication(blinded_id="blind_1", reviewer_id="r2", claim_support_passed=True),
    ]

    assert resolve_reviews(reviews) == {}


def test_independently_dual_reviewed_fields_resolve_together() -> None:
    reviews = [
        Adjudication(blinded_id="blind_1", reviewer_id="r1", observed_route="answer"),
        Adjudication(
            blinded_id="blind_1",
            reviewer_id="r2",
            observed_route="answer",
            claim_support_passed=True,
        ),
        Adjudication(blinded_id="blind_1", reviewer_id="r3", claim_support_passed=True),
    ]

    decision = resolve_reviews(reviews)["blind_1"]

    assert decision.observed_route.value == "answer"
    assert decision.claim_support_passed is True
    assert decision.reviewer_count == 3


# Testing that two independent reviews with the same blinded_id but different observed_route values
# do not resolve without an explicit resolution provided.
def test_disagreement_requires_explicit_resolution() -> None:
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
