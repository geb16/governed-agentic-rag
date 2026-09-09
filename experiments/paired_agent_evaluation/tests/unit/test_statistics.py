from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.statistics import (
    estimate_condition,
    estimate_paired_difference,
    registered_strata,
)
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.scores import Estimate, MetricContribution


def test_case_cluster_bootstrap_is_reproducible(paths) -> None:
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)[:2]
    contributions = [
        MetricContribution(
            key=ExecutionKey(case_id=case.case_id, repetition=1, condition=Condition.BASELINE),
            metric_id="metric",
            eligible=True,
            numerator=float(index),
            denominator=1,
        )
        for index, case in enumerate(cases)
    ]

    def run_estimate() -> Estimate:
        return estimate_condition(
            contributions,
            {case.case_id: case for case in cases},
            metric_id="metric",
            condition="baseline",
            stratum="overall",
            include_case=lambda _: True,
            replicates=100,
            seed=7,
            minimum_valid=90,
            stratify_by_category=True,
        )

    assert run_estimate() == run_estimate()

# Testing if the registered strata are used to control the resampling 
# policy, rather than the case IDs themselves.
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    contributions = [
        MetricContribution(
            key=ExecutionKey(case_id=case.case_id, repetition=1, condition=Condition.BASELINE),
            metric_id="metric",
            eligible=True,
            numerator=1,
            denominator=1,
        )
        for case in cases
    ]
    observed_groups = []

    def capture_draw(groups, _rng):
        observed_groups.append(groups)
        return [case_id for group in groups for case_id in group]

    monkeypatch.setattr(
        "paired_agent_evaluation.application.statistics._draw_case_ids", capture_draw
    )
    estimate_condition(
        contributions,
        {case.case_id: case for case in cases},
        metric_id="metric",
        condition="baseline",
        stratum="route=answer",
        include_case=lambda _: True,
        replicates=1,
        seed=7,
        minimum_valid=1,
        stratify_by_category=False,
    )

    assert len(observed_groups[0]) == 1

# Testing if the registered strata are used to control the resampling policy,
# rather than the case IDs themselves.
def test_registered_strata_encode_the_frozen_resampling_policy(paths) -> None:
    """Stratify only overall and category-macro bootstrap draws."""
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    policies = {
        name: (stratify_by_category, category_macro)
        for name, _, stratify_by_category, category_macro in registered_strata(cases)
    }

    assert policies.pop("overall") == (True, False)
    assert policies.pop("category_macro") == (True, True)
    assert set(policies.values()) == {(False, False)}

# Testing if the category-macro stratum is unweighted by category size, 
# so that each category contributes equally to the overall estimate.
def test_category_macro_is_unweighted(paths) -> None:
    """Average category ratios without weighting them by category size."""
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    case_map = {case.case_id: case for case in cases}
    categories = sorted({case.category.value for case in cases})
    contributions = [
        MetricContribution(
            key=ExecutionKey(case_id=case.case_id, repetition=1, condition=condition),
            metric_id="metric",
            eligible=True,
            numerator=float(categories.index(case.category.value) == 0),
            denominator=1,
        )
        for case in cases
        for condition in (Condition.BASELINE, Condition.GOVERNED)
    ]
    result = estimate_condition(
        contributions,
        case_map,
        metric_id="metric",
        condition="baseline",
        stratum="category_macro",
        include_case=lambda _: True,
        replicates=10,
        seed=7,
        minimum_valid=10,
        stratify_by_category=True,
        category_macro=True,
    )

    assert result.estimate == 1 / len(categories)

    difference = estimate_paired_difference(
        contributions,
        case_map,
        metric_id="metric",
        stratum="category_macro",
        include_case=lambda _: True,
        replicates=10,
        seed=7,
        minimum_valid=10,
        stratify_by_category=True,
        category_macro=True,
    )
    assert difference.governed_minus_baseline == 0
