"""Build deterministic tabular evidence from the sealed experiment results."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from formatting import format_value

from evidence.evidence_config import CONDITIONS, METRIC_LABELS
from evidence.evidence_io import ReleaseData, write_csv


def generate_tables(data: ReleaseData, output: Path) -> None:
    """Generate every Phase 7 CSV table.

    Args:
        data: Verified inputs from the sealed Phase 6 release.
        output: Directory in which to write the evidence tables.

    """
    _write_overall_results(data.estimates, data.differences, output)
    _write_stratified_effects(data.differences, output)
    _write_metric_denominators(data.scores, output)
    _write_operational_summary(data.summary, data.normalized, data.ragas, output)
    _write_categorical_counts(data.normalized, output)


def _write_overall_results(
    estimates: list[dict[str, Any]],
    differences: list[dict[str, Any]],
    output: Path,
) -> None:
    """Write condition estimates and paired effects for overall metrics."""
    overall_estimates = [row for row in estimates if row["stratum"] == "overall"]
    estimate_lookup = {(row["metric_id"], row["condition"]): row for row in overall_estimates}
    overall_differences = [row for row in differences if row["stratum"] == "overall"]
    rows = []
    for row in overall_differences:
        metric = row["metric_id"]
        baseline = estimate_lookup[(metric, "baseline")]
        governed = estimate_lookup[(metric, "governed")]
        rows.append(
            [
                metric,
                format_value(baseline["estimate"]),
                _interval(baseline["ci_lower"], baseline["ci_upper"]),
                format_value(governed["estimate"]),
                _interval(governed["ci_lower"], governed["ci_upper"]),
                format_value(row["governed_minus_baseline"]),
                _interval(row["ci_lower"], row["ci_upper"]),
                row["complete_pairs"],
                row["eligible_case_clusters"],
            ]
        )
    write_csv(
        output / "overall-results.csv",
        [
            "metric_id",
            "baseline",
            "baseline_ci",
            "governed",
            "governed_ci",
            "difference",
            "difference_ci",
            "complete_pairs",
            "eligible_case_clusters",
        ],
        rows,
    )


def _write_stratified_effects(differences: list[dict[str, Any]], output: Path) -> None:
    """Write paired effects for every non-overall analysis stratum."""
    rows = [
        [
            row["metric_id"],
            row["stratum"],
            format_value(row["governed_minus_baseline"]),
            format_value(row["ci_lower"]),
            format_value(row["ci_upper"]),
            row["complete_pairs"],
            row["eligible_case_clusters"],
            row["valid_bootstrap_replicates"],
        ]
        for row in differences
        if row["stratum"] != "overall"
    ]
    write_csv(
        output / "stratified-paired-effects.csv",
        [
            "metric_id",
            "stratum",
            "difference",
            "ci_lower",
            "ci_upper",
            "complete_pairs",
            "eligible_case_clusters",
            "valid_bootstrap_replicates",
        ],
        rows,
    )


def _write_metric_denominators(scores: list[dict[str, Any]], output: Path) -> None:
    """Write eligible counts and contribution totals by metric and condition."""
    contributions: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in scores:
        contributions[(row["metric_id"], row["key"]["condition"])].append(row)

    rows = []
    for metric in METRIC_LABELS:
        for condition in CONDITIONS:
            eligible = [row for row in contributions[(metric, condition)] if row["eligible"]]
            rows.append(
                [
                    metric,
                    condition,
                    len(eligible),
                    format_value(sum(float(row["numerator"]) for row in eligible)),
                    format_value(sum(float(row["denominator"]) for row in eligible)),
                ]
            )
    write_csv(
        output / "metric-denominators.csv",
        ["metric_id", "condition", "eligible_observations", "numerator_sum", "denominator_sum"],
        rows,
    )


def _write_operational_summary(
    summary: dict[str, Any],
    normalized: list[dict[str, Any]],
    ragas: list[dict[str, Any]],
    output: Path,
) -> None:
    """Write latency, token-use, and secondary-groundedness summaries."""
    latency: dict[str, list[float]] = defaultdict(list)
    for row in normalized:
        latency[row["key"]["condition"]].append(float(row["latency_ms"]))

    ragas_values: dict[str, list[float]] = defaultdict(list)
    for row in ragas:
        condition = row["observation_id"].rsplit("__", 1)[-1]
        ragas_values[condition].append(float(row["value"]))

    rows = []
    for condition in CONDITIONS:
        token_data = summary["token_usage_by_condition"][condition]
        values = latency[condition]
        rows.append(
            [
                condition,
                len(values),
                f"{statistics.median(values):.3f}",
                f"{_percentile(values, 0.25):.3f}",
                f"{_percentile(values, 0.75):.3f}",
                f"{statistics.mean(values):.3f}",
                token_data["input_tokens"],
                token_data["output_tokens"],
                token_data["input_tokens"] + token_data["output_tokens"],
                len(ragas_values[condition]),
                f"{statistics.mean(ragas_values[condition]):.6f}",
            ]
        )
    write_csv(
        output / "operational-summary.csv",
        [
            "condition",
            "observations",
            "median_latency_ms",
            "latency_q1_ms",
            "latency_q3_ms",
            "mean_latency_ms",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "ragas_eligible",
            "ragas_mean",
        ],
        rows,
    )


def _percentile(values: list[float], probability: float) -> float:
    """Estimate a percentile by linear interpolation between adjacent values.

    Args:
        values: Nonempty sample of numeric observations.
        probability: Quantile probability on the closed interval from zero to one.

    Returns:
        Interpolated percentile value.

    """
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_categorical_counts(normalized: list[dict[str, Any]], output: Path) -> None:
    """Write terminal-error and observed-route counts by condition."""
    terminal_errors: Counter[tuple[str, str]] = Counter()
    routes: Counter[tuple[str, str]] = Counter()
    for row in normalized:
        condition = row["key"]["condition"]
        terminal_errors[(condition, row["terminal_error_code"] or "none")] += 1
        routes[(condition, row["observed_route"] or "none")] += 1
    write_csv(
        output / "terminal-errors.csv",
        ["condition", "terminal_error_code", "count"],
        [
            [condition, error, count]
            for (condition, error), count in sorted(terminal_errors.items())
        ],
    )
    write_csv(
        output / "observed-routes.csv",
        ["condition", "observed_route", "count"],
        [[condition, route, count] for (condition, route), count in sorted(routes.items())],
    )


def _interval(lower: float | None, upper: float | None) -> str:
    """Format optional lower and upper confidence limits as an interval."""
    return f"[{format_value(lower)}, {format_value(upper)}]"
