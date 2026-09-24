"""Render selected overall estimates for the two experimental conditions."""

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

from pathlib import Path
from typing import Any

from evidence.evidence_config import CONDITIONS, METRIC_LABELS
from formatting import format_value

from figures.style import (
    BACKGROUND,
    BASELINE,
    FONT_FAMILY,
    GOVERNED,
    GRID,
    MUTED_TEXT,
    ROW_BAND,
    SECONDARY_TEXT,
    TEXT,
    TITLE,
)
from figures.svg_utils import text, word_svg_root, write_svg

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

SVG_WIDTH = 1000
SVG_HEIGHT = 760
PLOT_LEFT = 330
PLOT_WIDTH = 540
FIRST_ROW_Y = 196
ROW_HEIGHT = 65


def render_condition_estimates(estimates: list[dict[str, Any]], target: Path) -> None:
    """Render legible horizontal condition bars for selected metrics.

    Args:
        estimates: Metric estimates containing overall rows for both conditions.
        target: Destination path for the generated SVG figure.

    """
    lookup = {
        (row["metric_id"], row["condition"]): row
        for row in estimates
        if row["stratum"] == "overall"
    }
    parts = [
        word_svg_root(SVG_WIDTH, SVG_HEIGHT),
        '<title id="title">Selected overall condition estimates</title>',
        '<desc id="desc">Horizontal grouped bars compare baseline and governed point estimates for eight selected preregistered metrics.</desc>',
        f'<rect width="100%" height="100%" fill="{BACKGROUND}"/>',
        text(
            30,
            48,
            "Selected overall condition estimates",
            font_family=FONT_FAMILY,
            font_size="30",
            font_weight="700",
            fill=TITLE,
        ),
        text(
            30,
            79,
            "Registered proportions; higher values are better for every metric shown",
            font_family=FONT_FAMILY,
            font_size="17",
            fill=MUTED_TEXT,
        ),
    ]
    _add_legend(parts)
    _add_row_backgrounds(parts)
    _add_axis(parts)
    for index, metric in enumerate(SELECTED_METRICS):
        _add_metric_group(parts, lookup, metric, FIRST_ROW_Y + index * ROW_HEIGHT)
    write_svg(target, parts)


def _add_legend(parts: list[str]) -> None:
    """Append the condition legend at an easily legible size."""
    entries = (
        (664, BASELINE, "Baseline"),
        (820, GOVERNED, "Governed"),
    )
    for x_position, colour, label in entries:
        parts.append(
            f'<rect x="{x_position}" y="109" width="25" height="15" rx="3" fill="{colour}"/>'
        )
        parts.append(
            text(
                x_position + 35,
                123,
                label,
                font_family=FONT_FAMILY,
                font_size="16",
                font_weight="600",
                fill=SECONDARY_TEXT,
            )
        )


def _add_row_backgrounds(parts: list[str]) -> None:
    """Append alternating row bands behind the chart grid."""
    for index in range(0, len(SELECTED_METRICS), 2):
        y = FIRST_ROW_Y + index * ROW_HEIGHT
        parts.append(
            f'<rect x="26" y="{y - 29}" width="950" height="58" rx="4" fill="{ROW_BAND}"/>'
        )


def _add_axis(parts: list[str]) -> None:
    """Append the zero-to-one scale and vertical grid lines."""
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        x_position = PLOT_LEFT + tick * PLOT_WIDTH
        parts.append(
            f'<line x1="{x_position:.1f}" y1="166" x2="{x_position:.1f}" y2="{SVG_HEIGHT - 58}" stroke="{GRID}" stroke-width="1.2"/>'
        )
        parts.append(
            text(
                x_position,
                SVG_HEIGHT - 28,
                f"{tick:.2f}",
                text_anchor="middle",
                font_family=FONT_FAMILY,
                font_size="16",
                fill=MUTED_TEXT,
            )
        )
    parts.append(
        text(
            PLOT_LEFT + PLOT_WIDTH / 2,
            151,
            "Estimated proportion",
            text_anchor="middle",
            font_family=FONT_FAMILY,
            font_size="16",
            font_weight="700",
            fill=SECONDARY_TEXT,
        )
    )


def _add_metric_group(
    parts: list[str],
    lookup: dict[tuple[str, str], dict[str, Any]],
    metric: str,
    y: int,
) -> None:
    """Append one labelled pair of horizontal condition bars."""
    parts.append(
        text(
            306,
            y + 6,
            METRIC_LABELS[metric],
            text_anchor="end",
            font_family=FONT_FAMILY,
            font_size="18",
            fill=TEXT,
        )
    )
    offsets = dict(zip(CONDITIONS, (-13, 13), strict=True))
    colours = {"baseline": BASELINE, "governed": GOVERNED}
    for condition in CONDITIONS:
        offset = offsets[condition]
        colour = colours[condition]
        value = lookup[(metric, condition)]["estimate"]
        bar_width = 0 if value is None else value * PLOT_WIDTH
        parts.append(
            f'<rect x="{PLOT_LEFT}" y="{y + offset - 8}" width="{bar_width:.1f}" height="17" rx="3" fill="{colour}"/>'
        )
        label_x = round(min(PLOT_LEFT + bar_width + 11, 950), 1)
        parts.append(
            text(
                label_x,
                y + offset + 6,
                format_value(value),
                font_family=FONT_FAMILY,
                font_size="16",
                font_weight="700",
                fill=SECONDARY_TEXT,
            )
        )
