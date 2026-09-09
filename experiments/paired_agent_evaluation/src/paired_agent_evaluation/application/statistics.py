# Frozen ratio estimators and case-cluster percentile bootstrap.

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


def _case_groups(
    case_ids: Iterable[str],
    cases: dict[str, EvaluationCase],
    *,
    stratify_by_category: bool,
) -> list[list[str]]:
    ordered = sorted(case_ids)
    if not stratify_by_category:
        return [ordered]
    by_category: dict[str, list[str]] = defaultdict(list)
    for case_id in ordered:
        by_category[cases[case_id].category.value].append(case_id)
    return [by_category[category] for category in sorted(by_category)]


def _draw_case_ids(groups: list[list[str]], rng: random.Random) -> list[str]:
    return [rng.choice(group) for group in groups for _ in range(len(group))]


def _category_macro(
    items: Iterable[MetricContribution], cases: dict[str, EvaluationCase]
) -> float | None:
    by_category: dict[str, list[MetricContribution]] = defaultdict(list)
    materialized = list(items)
    for item in materialized:
        by_category[cases[item.key.case_id].category.value].append(item)
    categories = sorted({case.category.value for case in cases.values()})
    category_values = [_ratio(by_category[category]) for category in categories]
    if not category_values or any(value is None for value in category_values):
        return None
    return sum(value for value in category_values if value is not None) / len(category_values)


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
    stratify_by_category: bool,
    category_macro: bool = False,
) -> Estimate:
    selected = [
        item
        for item in contributions
        if item.metric_id == metric_id
        and item.key.condition.value == condition
        and include_case(cases[item.key.case_id])
    ]
    by_case: dict[str, list[MetricContribution]] = defaultdict(list)
    for item in selected:
        by_case[item.key.case_id].append(item)
    groups = _case_groups(by_case, cases, stratify_by_category=stratify_by_category)
    aggregate = (lambda items: _category_macro(items, cases)) if category_macro else _ratio
    point = aggregate(selected)
    bootstrap: list[float] = []
    if len(by_case) >= 2:
        rng = random.Random(seed)
        for _ in range(replicates):
            draw = _draw_case_ids(groups, rng)
            value = aggregate(item for case_id in draw for item in by_case[case_id])
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
    stratify_by_category: bool,
    category_macro: bool = False,
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
    groups = _case_groups(pairs, cases, stratify_by_category=stratify_by_category)
    aggregate = (lambda items: _category_macro(items, cases)) if category_macro else _ratio

    def difference(ids: list[str]) -> float | None:
        baseline = aggregate(pair[0] for case_id in ids for pair in pairs[case_id])
        governed = aggregate(pair[1] for case_id in ids for pair in pairs[case_id])
        return governed - baseline if baseline is not None and governed is not None else None

    identities = list(pairs)
    point = difference(identities)
    bootstrap: list[float] = []
    if len(pairs) >= 2:
        rng = random.Random(seed)
        for _ in range(replicates):
            value = difference(_draw_case_ids(groups, rng))
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
) -> list[tuple[str, Callable[[EvaluationCase], bool], bool, bool]]:
    def include_all(_: EvaluationCase) -> bool:
        return True

    strata: list[tuple[str, Callable[[EvaluationCase], bool], bool, bool]] = [
        ("overall", include_all, True, False),
        ("category_macro", include_all, True, True),
    ]
    dimensions: dict[str, Callable[[EvaluationCase], str]] = {
        "category": lambda case: case.category.value,
        "route": lambda case: case.expected.route.value,
        "intent": lambda case: case.expected.intent,
        "risk_level": lambda case: case.expected.risk_level.value,
    }
    for dimension, accessor in dimensions.items():
        for value in sorted({accessor(case) for case in cases}):

            def matches(
                case: EvaluationCase,
                selected: str = value,
                read: Callable[[EvaluationCase], str] = accessor,
            ) -> bool:
                return read(case) == selected

            strata.append((f"{dimension}={value}", matches, False, False))
    return strata
