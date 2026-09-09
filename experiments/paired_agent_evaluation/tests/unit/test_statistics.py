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

