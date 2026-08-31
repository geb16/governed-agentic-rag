"""Protect the pre-registered scoring and common-harness contract."""

from app.evaluation.dataset import ScoringRubric


def test_rubric_has_no_composite_and_unique_metrics(rubric: ScoringRubric) -> None:
    """Keep metric identities unique and prohibit composite scoring.

    Args:
        rubric: Strict checked-in scoring rubric.
    """
    assert rubric.composite_score is None
    assert rubric.repetitions_per_case == 3
    metric_ids = [metric.metric_id for metric in rubric.metrics]
    assert len(metric_ids) == len(set(metric_ids))
    assert {
        "workflow_completion_rate",
        "unsafe_action_prevention_rate",
        "escalation_f1",
        "escalation_precision",
        "escalation_recall",
        "recovery_success_rate",
        "groundedness_rate",
        "audit_trace_completeness",
    }.issubset(metric_ids)


def test_every_metric_defines_eligibility_and_failure_policy(
    rubric: ScoringRubric,
) -> None:
    """Require every metric to define its scoring population and failures.

    Args:
        rubric: Strict checked-in scoring rubric.
    """
    for metric in rubric.metrics:
        assert metric.eligible_when
        assert metric.numerator
        assert metric.denominator
        assert metric.failure_policy


def test_statistical_protocol_is_fully_preregistered(rubric: ScoringRubric) -> None:
    """Lock estimation choices before test-split results can influence them.

    Args:
        rubric: Strict checked-in scoring rubric.
    """
    protocol = rubric.statistical_protocol

    assert protocol.condition_order_method == "sha256_seeded_alternating"
    assert protocol.condition_order_seed == 20260831
    assert "first digest byte" in protocol.condition_order_policy
    assert "even-numbered repetition" in protocol.condition_order_policy
    assert "Never revise" in protocol.condition_order_policy
    assert protocol.confidence_level == 0.95
    assert protocol.bootstrap_method == "nonparametric_percentile_case_cluster"
    assert protocol.bootstrap_replicates == 10_000
    assert protocol.bootstrap_seed == 20260830
    assert "all three repetitions and both conditions" in protocol.resampling_policy
    assert "same complete case-by-repetition pairs" in protocol.paired_difference_policy
    assert "TP+FP is zero" in protocol.zero_denominator_policy
    assert "complete pairs only" in protocol.missing_observation_policy
    assert "no null-hypothesis significance tests" in protocol.multiplicity_policy
