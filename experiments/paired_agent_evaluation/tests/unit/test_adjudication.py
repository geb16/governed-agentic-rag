from paired_agent_evaluation.application.adjudication import resolve_reviews
from paired_agent_evaluation.domain.scores import Adjudication, ResolvedAdjudication


# Testing that two independent reviews with the same blinded_id and the same 
# observed_route value resolve to that value.
def test_two_independent_matching_reviews_resolve() -> None:
    reviews = [
        Adjudication(blinded_id="blind_1", reviewer_id="r1", observed_route="answer"),
        Adjudication(blinded_id="blind_1", reviewer_id="r2", observed_route="answer"),
    ]
    assert resolve_reviews(reviews)["blind_1"].observed_route.value == "answer"

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
