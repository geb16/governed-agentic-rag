from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.statistics import (
    estimate_condition,
    estimate_paired_difference,
    registered_strata,
)
from paired_agent_evaluation.domain.executions import Condition, ExecutionKey
from paired_agent_evaluation.domain.scores import MetricContribution


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
    kwargs = dict(
        contributions=contributions,
        cases={case.case_id: case for case in cases},
        metric_id="metric",
        condition="baseline",
        stratum="overall",
        include_case=lambda _: True,
        replicates=100,
        seed=7,
        minimum_valid=90,
        stratify_by_category=True,
    )
    assert estimate_condition(**kwargs) == estimate_condition(**kwargs)


def test_bootstrap_resamples_case_ids_not_categories_when_unstratified(paths, monkeypatch) -> None:
    """Draw from one pooled group of case ids, not per-category groups, when unstratified."""
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


def test_only_aggregate_strata_resample_by_category(paths) -> None:
    """Apply category-stratified resampling only to aggregate estimates."""
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    policies = {
        name: (stratified, category_macro)
        for name, _, stratified, category_macro in registered_strata(cases)
    }

    assert policies["overall"] == (True, False)
    assert policies["category_macro"] == (True, True)
    assert all(
        policy == (False, False)
        for name, policy in policies.items()
        if name not in {"overall", "category_macro"}
    )


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
