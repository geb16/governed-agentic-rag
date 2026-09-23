"""Render the overall governed-minus-baseline paired-effects forest plot."""

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from evidence.evidence_config import METRIC_LABELS
from formatting import format_value

from figures.svg_utils import text, write_svg


def render_overall_effects(rows: list[dict[str, Any]], target: Path) -> None:
    """Render governed-minus-baseline effects and confidence intervals.

    Args:
        rows: Overall paired-difference records in display order.
        target: Destination path for the generated SVG figure.

    """
    width, plot_left, plot_width = 1200, 520, 560
    row_height, top = 49, 118
    height = top + row_height * len(rows) + 90
    x_min, x_max = -0.55, 0.65

    def x(value: float) -> float:
        """Map an effect value onto the horizontal plot coordinate."""
        return plot_left + (value - x_min) / (x_max - x_min) * plot_width

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Overall paired effects of governance</title>',
        '<desc id="desc">Forest plot of governed minus baseline effects and pointwise 95 percent confidence intervals for fourteen preregistered metrics.</desc>',
        '<rect width="100%" height="100%" fill="#fbfcfe"/>',
        text(
            44,
            46,
            "Overall paired effects (governed - baseline)",
            font_family="Arial",
            font_size="25",
            font_weight="700",
            fill="#172554",
        ),
        text(
            44,
            78,
            "Pointwise 95% case-cluster bootstrap intervals; NA = not estimable",
            font_family="Arial",
            font_size="15",
            fill="#475569",
        ),
    ]
    _add_axis(parts, x, height)
    for index, row in enumerate(rows):
        _add_metric_row(parts, row, index, x, top, row_height, plot_left, plot_width)
    parts.append(
        text(
            plot_left + plot_width / 2,
            height - 5,
            "Difference on registered metric scale",
            text_anchor="middle",
            font_family="Arial",
            font_size="14",
            fill="#334155",
        )
    )
    write_svg(target, parts)


def _add_axis(parts: list[str], x: Callable[[float], float], height: int) -> None:
    """Append the effect-scale grid, zero line, and tick labels."""
    for tick in (-0.5, -0.25, 0.0, 0.25, 0.5):
        colour = "#334155" if tick == 0 else "#dbe3ee"
        stroke_width = 2 if tick == 0 else 1
        parts.append(
            f'<line x1="{x(tick):.1f}" y1="96" x2="{x(tick):.1f}" y2="{height - 54}" stroke="{colour}" stroke-width="{stroke_width}"/>'
        )
        parts.append(
            text(
                x(tick),
                height - 28,
                f"{tick:+.2f}",
                text_anchor="middle",
                font_family="Arial",
                font_size="13",
                fill="#475569",
            )
        )


def _add_metric_row(
    parts: list[str],
    row: dict[str, Any],
    index: int,
    x: Callable[[float], float],
    top: int,
    row_height: int,
    plot_left: int,
    plot_width: int,
) -> None:
    """Append one labelled effect estimate and its confidence interval."""
    y = top + index * row_height
    if index % 2 == 0:
        parts.append(f'<rect x="30" y="{y - 27}" width="1135" height="43" rx="5" fill="#f1f5f9"/>')
    parts.append(
        text(
            290,
            y,
            METRIC_LABELS[row["metric_id"]],
            text_anchor="end",
            font_family="Arial",
            font_size="14",
            fill="#0f172a",
        )
    )
    effect = row["governed_minus_baseline"]
    lower, upper = row["ci_lower"], row["ci_upper"]
    if effect is None:
        parts.append(
            text(
                plot_left + plot_width / 2,
                y,
                "NA",
                text_anchor="middle",
                font_family="Arial",
                font_size="14",
                fill="#64748b",
            )
        )
        value_text = "NA"
    else:
        if lower is not None and upper is not None:
            parts.append(
                f'<line x1="{x(lower):.1f}" y1="{y - 5}" x2="{x(upper):.1f}" y2="{y - 5}" stroke="#2563eb" stroke-width="5" stroke-linecap="round"/>'
            )
        colour = "#0f766e" if effect >= 0 else "#c2410c"
        parts.append(
            f'<circle cx="{x(effect):.1f}" cy="{y - 5}" r="7" fill="{colour}" stroke="#ffffff" stroke-width="2"/>'
        )
        value_text = f"{effect:+.3f} [{format_value(lower)}, {format_value(upper)}]"
    parts.append(
        text(
            1110,
            y,
            value_text,
            text_anchor="end",
            font_family="Arial",
            font_size="13",
            fill="#334155",
        )
    )
