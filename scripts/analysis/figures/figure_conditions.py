# Render selected overall metric estimates by experimental condition.

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

from pathlib import Path
from typing import Any

from evidence.evidence_config import METRIC_LABELS
from formatting import format_value

from figures.svg_utils import text, write_svg

SELECTED_METRICS = (
    "appropriate_route_rate",
    "workflow_completion_rate",
    "action_correctness_rate",
    "unsafe_action_prevention_rate",
    "recovery_success_rate",
    "groundedness_rate",
    "context_precision",
    "audit_trace_completeness",
)


def render_condition_estimates(estimates: list[dict[str, Any]], target: Path) -> None:
    """Render grouped baseline and governed bars for selected metrics."""

    lookup = {
        (row["metric_id"], row["condition"]): row
        for row in estimates
        if row["stratum"] == "overall"
    }
    width, height, left, top, plot_height = 1240, 720, 245, 110, 500
    group_width = 112
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Overall condition estimates</title>',
        '<desc id="desc">Grouped bars compare baseline and governed point estimates for selected preregistered metrics.</desc>',
        '<rect width="100%" height="100%" fill="#fbfcfe"/>',
        text(
            40,
            45,
            "Overall condition estimates",
            font_family="Arial",
            font_size="25",
            font_weight="700",
            fill="#172554",
        ),
        '<rect x="875" y="35" width="18" height="18" fill="#64748b"/><text x="901" y="50" font-family="Arial" font-size="14" fill="#334155">Baseline</text>',
        '<rect x="995" y="35" width="18" height="18" fill="#0f766e"/><text x="1021" y="50" font-family="Arial" font-size="14" fill="#334155">Governed</text>',
    ]
    _add_y_axis(parts, left, top, plot_height)
    for index, metric in enumerate(SELECTED_METRICS):
        centre = left + 65 + index * group_width
        _add_bars(parts, lookup, metric, centre, top, plot_height)
        _add_label(parts, metric, centre)
    write_svg(target, parts)


def _add_y_axis(parts: list[str], left: int, top: int, plot_height: int) -> None:
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_height * (1 - tick)
        parts.append(f'<line x1="{left}" y1="{y}" x2="1185" y2="{y}" stroke="#dbe3ee"/>')
        parts.append(
            text(
                left - 12,
                y + 5,
                f"{tick:.2f}",
                text_anchor="end",
                font_family="Arial",
                font_size="13",
                fill="#475569",
            )
        )


def _add_bars(
    parts: list[str],
    lookup: dict[tuple[str, str], dict[str, Any]],
    metric: str,
    centre: int,
    top: int,
    plot_height: int,
) -> None:
    for offset, condition, colour in (
        (-19, "baseline", "#64748b"),
        (19, "governed", "#0f766e"),
    ):
        value = lookup[(metric, condition)]["estimate"]
        bar_height = 0 if value is None else value * plot_height
        parts.append(
            f'<rect x="{centre + offset - 16}" y="{top + plot_height - bar_height:.1f}" width="32" height="{bar_height:.1f}" rx="3" fill="{colour}"/>'
        )
        parts.append(
            text(
                centre + offset,
                top + plot_height - bar_height - 7,
                format_value(value),
                text_anchor="middle",
                font_family="Arial",
                font_size="11",
                fill="#334155",
            )
        )


def _add_label(parts: list[str], metric: str, centre: int) -> None:
    for line_index, line in enumerate(METRIC_LABELS[metric].split()):
        parts.append(
            text(
                centre,
                640 + line_index * 16,
                line,
                text_anchor="middle",
                font_family="Arial",
                font_size="12",
                fill="#334155",
            )
        )
