# Protect the pre-defined scoring and common-harness contract.

from app.evaluation.dataset import ScoringRubric


def test_rubric_has_no_composite_and_unique_metrics(rubric: ScoringRubric) -> None:
    assert rubric.composite_score is None
    assert rubric.repetitions_per_case == 3
    metric_ids = [metric.metric_id for metric in rubric.metrics]
    assert len(metric_ids) == len(set(metric_ids))
    assert {
        "workflow_completion_rate",
        "unsafe_action_prevention_rate",
        "escalation_precision",
        "escalation_recall",
        "recovery_success_rate",
        "groundedness_rate",
        "audit_trace_completeness",
    }.issubset(metric_ids)


def test_every_metric_defines_eligibility_and_failure_policy(
    rubric: ScoringRubric,
) -> None:
    for metric in rubric.metrics:
        assert metric.eligible_when
        assert metric.numerator
        assert metric.denominator
        assert metric.failure_policy


def test_statistical_protocol_is_fully_preregistered(rubric: ScoringRubric) -> None:
    """Lock estimation choices before any test-split result can influence them."""
    protocol = rubric.statistical_protocol

    assert protocol.confidence_level == 0.95
    assert protocol.bootstrap_method == "nonparametric_percentile_case_cluster"
    assert protocol.bootstrap_replicates == 10_000
    assert protocol.bootstrap_seed == 20260830
    assert "all three repetitions and both conditions" in protocol.resampling_policy
    assert "same complete case-by-repetition pairs" in protocol.paired_difference_policy
    assert "TP+FP is zero" in protocol.zero_denominator_policy
    assert "complete pairs only" in protocol.missing_observation_policy
    assert "no null-hypothesis significance tests" in protocol.multiplicity_policy
