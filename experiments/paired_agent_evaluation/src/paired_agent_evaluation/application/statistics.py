# Frozen ratio estimators and stratified case-cluster percentile bootstrap.

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable, Iterable

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.scores import Estimate, MetricContribution, PairedDifference


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


def estimate_paired_difference(
    contributions: list[MetricContribution],
    cases: dict[str, EvaluationCase],
    *,
    metric_id: str,
    stratum: str,
    include_case: Callable[[EvaluationCase], bool],
    replicates: int,
    seed: int,
    minimum_valid: int,
) -> PairedDifference:
    keyed = {
        (item.key.case_id, item.key.repetition, item.key.condition.value): item
        for item in contributions
        if item.metric_id == metric_id and include_case(cases[item.key.case_id])
    }
    pairs: dict[str, list[tuple[MetricContribution, MetricContribution]]] = defaultdict(list)
    pair_keys = {(case_id, repetition) for case_id, repetition, _ in keyed}
    for case_id, repetition in pair_keys:
        baseline = keyed.get((case_id, repetition, "baseline"))
        governed = keyed.get((case_id, repetition, "governed"))
        if (
            baseline is not None
            and governed is not None
            and baseline.pending_reason is None
            and governed.pending_reason is None
        ):
            pairs[case_id].append((baseline, governed))
    categories: dict[str, list[str]] = defaultdict(list)
    for case_id in sorted(pairs):
        categories[cases[case_id].category.value].append(case_id)

    def difference(ids: list[str]) -> float | None:
        baseline = _ratio(pair[0] for case_id in ids for pair in pairs[case_id])
        governed = _ratio(pair[1] for case_id in ids for pair in pairs[case_id])
        return governed - baseline if baseline is not None and governed is not None else None

    identities = list(pairs)
    point = difference(identities)
    bootstrap: list[float] = []
    if len(pairs) >= 2:
        rng = random.Random(seed)
        for _ in range(replicates):
            value = difference(_draw_case_ids(categories, rng))
            if value is not None:
                bootstrap.append(value)
    valid_interval = len(bootstrap) >= minimum_valid
    return PairedDifference(
        metric_id=metric_id,
        stratum=stratum,
        governed_minus_baseline=point,
        ci_lower=_percentile(bootstrap, 0.025) if valid_interval else None,
        ci_upper=_percentile(bootstrap, 0.975) if valid_interval else None,
        complete_pairs=sum(len(value) for value in pairs.values()),
        eligible_case_clusters=len(pairs),
        valid_bootstrap_replicates=len(bootstrap),
    )


def registered_strata(
    cases: list[EvaluationCase],
) -> list[tuple[str, Callable[[EvaluationCase], bool]]]:
    def include_all(_: EvaluationCase) -> bool:
        return True

    strata = [("overall", include_all)]
    dimensions: dict[str, Callable[[EvaluationCase], str]] = {
        "category": lambda case: case.category.value,
        "route": lambda case: casse.expected.route.value,
        "intent": lambda case: case.expected.intent,
        "risk_level": lambda case: case.expected.risk_level.value,
    }
    for dimension, accessor in dimensions.items():
        for value in sorted({accessor(case) for case in cases}):

            strata.append(f"{dimension}={value}")
    return strata
