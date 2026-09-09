from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.statistics import estimate_condition, registered_strata
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


def test_category_macro_is_unweighted_across_categories(paths) -> None:
    """Give each category equal weight regardless of its metric denominator."""
    cases = Phase5Dataset(paths.repository).cases(DatasetSplit.VALIDATION)
    first = cases[0]
    second = next(case for case in cases if case.category != first.category)
    selected = {case.case_id: case for case in (first, second)}
    contributions = [
        MetricContribution(
            key=ExecutionKey(case_id=first.case_id, repetition=1, condition=Condition.BASELINE),
            metric_id="metric",
            eligible=True,
            numerator=9,
            denominator=9,
        ),
        MetricContribution(
            key=ExecutionKey(case_id=second.case_id, repetition=1, condition=Condition.BASELINE),
            metric_id="metric",
            eligible=True,
            numerator=0,
            denominator=1,
        ),
    ]

    estimate = estimate_condition(
        contributions,
        selected,
        metric_id="metric",
        condition="baseline",
        stratum="category_macro",
        include_case=lambda _: True,
        replicates=0,
        seed=7,
        minimum_valid=1,
        stratify_by_category=True,
        category_macro=True,
    )

    assert estimate.estimate == 0.5
