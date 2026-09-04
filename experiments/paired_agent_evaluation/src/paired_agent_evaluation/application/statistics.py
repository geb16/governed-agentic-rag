# Frozen ratio estimators and stratified case-cluster percentile bootstrap.

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable, Iterable

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.scores import Estimate, MetricContribution


def _ratio(items: Iterable[MetricContribution]) -> float | None:
    values = [item for item in items if item.eligible and item.pending_reason is None]
    denominator = sum(item.denominator for item in values)
    return sum(item.numerator for item in values) / denominator if denominator else None


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _draw_case_ids(case_ids_by_category: dict[str, list[str]], rng: random.Random) -> list[str]:
    return [rng.choice(ids) for ids in case_ids_by_category.values() for _ in range(len(ids))]


def estimate_condition(
    contributions: list[MetricContribution],
    cases: dict[str, EvaluationCase],
    *,
    metric_id: str,
    condition: str,
    stratum: str,
    include_case: Callable[[EvaluationCase], bool],
    replicates: int,
    seed: int,
    minimum_valid: int,
) -> Estimate:
    selected = [
        item
        for item in contributions
        if item.metric_id == metric_id
        and item.key.condition.value == condition
        and include_case(cases[item.key.case_id])
    ]
    by_case: dict[str, list[MetricContribution]] = defaultdict(list)
    categories: dict[str, list[str]] = defaultdict(list)
    for item in selected:
        by_case[item.key.case_id].append(item)
    for case_id in sorted(by_case):
        categories[cases[case_id].category.value].append(case_id)
    point = _ratio(selected)
    bootstrap: list[float] = []
    if len(by_case) >= 2:
        rng = random.Random(seed)
        for _ in range(replicates):
            draw = _draw_case_ids(categories, rng)
            value = _ratio(item for case_id in draw for item in by_case[case_id])
            if value is not None:
                bootstrap.append(value)
    valid_interval = len(bootstrap) >= minimum_valid
    return Estimate(
        metric_id=metric_id,
        condition=condition,
        stratum=stratum,
        estimate=point,
        ci_lower=_percentile(bootstrap, 0.025) if valid_interval else None,
        ci_upper=_percentile(bootstrap, 0.975) if valid_interval else None,
        eligible_case_clusters=len(by_case),
        accepted_observations=len({(item.key.case_id, item.key.repetition) for item in selected}),
        valid_bootstrap_replicates=len(bootstrap),
    )
