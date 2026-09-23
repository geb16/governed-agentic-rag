"""Render the overall governed-minus-baseline paired-effects forest plot."""

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from evidence.evidence_config import METRIC_DIRECTIONS, METRIC_LABELS
from formatting import format_value

from figures.svg_utils import text, write_svg

FONT_FAMILY = "Aptos, Calibri, Arial, sans-serif"
BENEFICIAL = "#007A5E"
ADVERSE = "#C2410C"
NEUTRAL = "#64748B"

SVG_WIDTH = 1000
WORD_WIDTH_IN = 6.5
PLOT_LEFT = 330
PLOT_WIDTH = 390
RESULT_X = 974
ROW_HEIGHT = 48
FIRST_ROW_Y = 220
X_MIN = -0.55
X_MAX = 0.65


def render_overall_effects(rows: list[dict[str, Any]], target: Path) -> None:
    """Render paired effects on their registered numeric scale.

    Positions and reported values both use governed minus baseline. Marker
    colour communicates whether the observed direction is beneficial.

    Args:
        rows: Overall paired-difference records in display order.
        target: Destination path for the generated SVG figure.

    """
    height = FIRST_ROW_Y + ROW_HEIGHT * len(rows) + 104
    physical_height = height / SVG_WIDTH * WORD_WIDTH_IN

    def x(value: float) -> float:
        """Map a governed-minus-baseline effect onto the plot coordinate."""
        return PLOT_LEFT + (value - X_MIN) / (X_MAX - X_MIN) * PLOT_WIDTH

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WORD_WIDTH_IN}in" height="{physical_height:.2f}in" viewBox="0 0 {SVG_WIDTH} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Overall paired effects of governance</title>',
        '<desc id="desc">Forest plot of governed minus baseline effects and pointwise 95 percent confidence intervals. Positions remain on the registered metric scale; marker colours account for whether higher or lower values are desirable.</desc>',
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        text(
            30,
            48,
            "Overall paired effects of governance",
            font_family=FONT_FAMILY,
            font_size="30",
            font_weight="700",
            fill="#16324F",
        ),
        text(
            30,
            78,
            "Pointwise 95% case-cluster bootstrap intervals",
            font_family=FONT_FAMILY,
            font_size="17",
            fill="#475569",
        ),
        text(
            30,
            104,
            "Positions and reported values are governed - baseline; colour indicates desirability",
            font_family=FONT_FAMILY,
            font_size="16",
            fill="#475569",
        ),
    ]
    _add_legend(parts)
    _add_row_backgrounds(parts, len(rows))
    _add_axis(parts, x, height)
    _add_headers(parts)
    for index, row in enumerate(rows):
        _add_metric_row(parts, row, index, x)
    parts.append(
        text(
            PLOT_LEFT + PLOT_WIDTH / 2,
            height - 17,
            "Governed - baseline effect on the registered metric scale",
            text_anchor="middle",
            font_family=FONT_FAMILY,
            font_size="15",
            font_weight="600",
            fill="#334155",
        )
    )
    write_svg(target, parts)


def _add_legend(parts: list[str]) -> None:
    """Append the direction-aware marker legend."""
    entries = (
        (390, BENEFICIAL, "Favours governed"),
        (596, ADVERSE, "Favours baseline"),
        (786, NEUTRAL, "No difference"),
    )
    for x_position, colour, label in entries:
        parts.append(
            f'<circle cx="{x_position}" cy="137" r="7" fill="{colour}" stroke="#FFFFFF" stroke-width="1.5"/>'
        )
        parts.append(
            text(
                x_position + 14,
                143,
                label,
                font_family=FONT_FAMILY,
                font_size="15",
                fill="#334155",
            )
        )


def _add_headers(parts: list[str]) -> None:
    """Append unobstructed column headings above the forest plot."""
    parts.extend(
        [
            text(
                306,
                188,
                "Metric",
                text_anchor="end",
                font_family=FONT_FAMILY,
                font_size="16",
                font_weight="700",
                fill="#334155",
            ),
            text(
                RESULT_X,
                188,
                "Reported effect [95% CI]",
                text_anchor="end",
                font_family=FONT_FAMILY,
                font_size="16",
                font_weight="700",
                fill="#334155",
            ),
            '<line x1="26" y1="199" x2="976" y2="199" stroke="#CBD5E1" stroke-width="1.5"/>',
        ]
    )


def _add_row_backgrounds(parts: list[str], row_count: int) -> None:
    """Append alternating row bands behind all foreground content."""
    for index in range(0, row_count, 2):
        y = FIRST_ROW_Y + index * ROW_HEIGHT
        parts.append(f'<rect x="26" y="{y - 24}" width="950" height="44" rx="4" fill="#F5F7FA"/>')


def _add_axis(parts: list[str], x: Callable[[float], float], height: int) -> None:
    """Append the registered effect-scale grid, zero line, and tick labels."""
    for tick in (-0.5, -0.25, 0.0, 0.25, 0.5):
        colour = "#475569" if tick == 0 else "#DCE3EA"
        stroke_width = 2 if tick == 0 else 1
        parts.append(
            f'<line x1="{x(tick):.1f}" y1="202" x2="{x(tick):.1f}" y2="{height - 72}" stroke="{colour}" stroke-width="{stroke_width}"/>'
        )
        parts.append(
            text(
                x(tick),
                height - 48,
                f"{tick:+.2f}",
                text_anchor="middle",
                font_family=FONT_FAMILY,
                font_size="15",
                fill="#475569",
            )
        )


def _add_metric_row(
    parts: list[str],
    row: dict[str, Any],
    index: int,
    x: Callable[[float], float],
) -> None:
    """Append one labelled estimate on the registered numeric scale."""
    y = FIRST_ROW_Y + index * ROW_HEIGHT
    metric = row["metric_id"]
    label = METRIC_LABELS[metric]
    if METRIC_DIRECTIONS[metric] == "lower":
        label = f"{label} (lower is better)"
    parts.append(
        text(
            306,
            y,
            label,
            text_anchor="end",
            font_family=FONT_FAMILY,
            font_size="17",
            fill="#172033",
        )
    )
    effect = row["governed_minus_baseline"]
    lower, upper = row["ci_lower"], row["ci_upper"]
    if effect is None:
        parts.append(
            text(
                PLOT_LEFT + PLOT_WIDTH / 2,
                y,
                "NA",
                text_anchor="middle",
                font_family=FONT_FAMILY,
                font_size="16",
                font_weight="700",
                fill=NEUTRAL,
            )
        )
        value_text = "NA"
    else:
        if lower is not None and upper is not None:
            parts.extend(
                [
                    f'<line x1="{x(lower):.1f}" y1="{y - 6}" x2="{x(upper):.1f}" y2="{y - 6}" stroke="#52677D" stroke-width="4" stroke-linecap="round"/>',
                    f'<line x1="{x(lower):.1f}" y1="{y - 12}" x2="{x(lower):.1f}" y2="{y}" stroke="#52677D" stroke-width="2"/>',
                    f'<line x1="{x(upper):.1f}" y1="{y - 12}" x2="{x(upper):.1f}" y2="{y}" stroke="#52677D" stroke-width="2"/>',
                ]
            )
        colour = _effect_colour(metric, effect)
        parts.append(
            f'<circle cx="{x(effect):.1f}" cy="{y - 6}" r="8" fill="{colour}" stroke="#FFFFFF" stroke-width="2"/>'
        )
        value_text = f"{effect:+.3f} [{format_value(lower)}, {format_value(upper)}]"
    parts.append(
        text(
            RESULT_X,
            y,
            value_text,
            text_anchor="end",
            font_family=FONT_FAMILY,
            font_size="16",
            font_weight="600",
            fill="#263548",
        )
    )


def _effect_colour(metric: str, effect: float) -> str:
    """Return a direction-aware colour without changing numeric position."""
    if effect == 0:
        return NEUTRAL
    governed_benefits = effect < 0 if METRIC_DIRECTIONS[metric] == "lower" else effect > 0
    return BENEFICIAL if governed_benefits else ADVERSE
