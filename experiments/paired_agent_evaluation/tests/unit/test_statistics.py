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
# policy, rather than the case IDs themselves. This is important because the case IDs are not guaranteed to be stable across runs, but the registered strata should be.
def test_reported_stratum_resamples_as_one_case_pool(paths, monkeypatch) -> None:
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
