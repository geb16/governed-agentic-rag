"""Build deterministic tabular evidence from the sealed experiment results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evidence_io import ReleaseData, write_csv
from figures.svg_utils import format_value


def generate_tables(data: ReleaseData, output: Path) -> None:
    """Generate every Phase 7 CSV table."""

    _write_overall_results(data.estimates, data.differences, output)
    


def _write_overall_results(
    estimates: list[dict[str, Any]],
    differences: list[dict[str, Any]],
    output: Path,
) -> None:
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


def _interval(lower: float | None, upper: float | None) -> str:
    return f"[{format_value(lower)}, {format_value(upper)}]"

