"""Render Word-ready operational latency and token-use indicators."""

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from evidence.evidence_config import CONDITIONS, Condition

from figures.style import (
    BACKGROUND,
    BASELINE,
    FONT_FAMILY,
    GOVERNED,
    MUTED_TEXT,
    ROW_BAND,
    SECONDARY_TEXT,
    TITLE,
)
from figures.svg_utils import text, word_svg_root, write_svg

SVG_WIDTH = 1000
SVG_HEIGHT = 390
BAR_WIDTH = 285
CONDITION_COLOURS = {"baseline": BASELINE, "governed": GOVERNED}


def render_operational_indicators(
    summary: dict[str, Any],
    normalized: list[dict[str, Any]],
    target: Path,
) -> None:
    """Render separate-scale panels for latency and token usage.

    Args:
        summary: Sealed run summary containing token totals by condition.
        normalized: Normalized observations containing per-request latency.
        target: Destination path for the generated SVG figure.

    Raises:
        ValueError: If a condition has no latency observations.

    """
    latency: dict[str, list[float]] = defaultdict(list)
    for row in normalized:
        latency[row["key"]["condition"]].append(float(row["latency_ms"]))
    missing = [condition for condition in CONDITIONS if not latency[condition]]
    if missing:
        raise ValueError(f"Missing latency observations for: {', '.join(missing)}")

    tokens = summary["token_usage_by_condition"]
    latency_values: dict[Condition, float] = {
        condition: statistics.median(latency[condition]) / 1000 for condition in CONDITIONS
    }
    token_totals: dict[Condition, int] = {
        condition: tokens[condition]["input_tokens"] + tokens[condition]["output_tokens"]
        for condition in CONDITIONS
    }
    token_values: dict[Condition, float] = {
        condition: token_totals[condition] / 10000 for condition in CONDITIONS
    }
    token_note = (
        f"{token_values['baseline']:.2f} = {token_totals['baseline']:,}; "
        f"{token_values['governed']:.2f} = {token_totals['governed']:,} tokens"
    )
    parts = [
        word_svg_root(SVG_WIDTH, SVG_HEIGHT),
        '<title id="title">Operational indicators</title>',
        '<desc id="desc">Separate panels compare median latency in seconds and total token usage for the baseline and governed conditions. Token values are totals expressed in units of 10,000 tokens.</desc>',
        f'<rect width="100%" height="100%" fill="{BACKGROUND}"/>',
        text(
            30,
            48,
            "Operational indicators",
            font_family=FONT_FAMILY,
            font_size="30",
            font_weight="700",
            fill=TITLE,
        ),
        text(
            30,
            79,
            "Panels use independent scales; conditions are compared within each panel",
            font_family=FONT_FAMILY,
            font_size="17",
            fill=MUTED_TEXT,
        ),
    ]
    panels = (
        (30, "Median latency (seconds)", latency_values, "s", None),
        (
            520,
            "Total token usage (x10,000-tokens)",
            token_values,
            "",
            token_note,
        ),
    )
    for panel_x, title, values, suffix, note in panels:
        _add_panel(parts, panel_x, title, values, suffix, note)
    write_svg(target, parts)


def _add_panel(
    parts: list[str],
    panel_x: int,
    title: str,
    values: dict[Condition, float],
    suffix: str,
    note: str | None,
) -> None:
    """Append one independently scaled operational comparison panel."""
    parts.append(f'<rect x="{panel_x}" y="105" width="450" height="240" rx="8" fill="{ROW_BAND}"/>')
    parts.append(
        text(
            panel_x + 20,
            139,
            title,
            font_family=FONT_FAMILY,
            font_size="19",
            font_weight="700",
            fill=SECONDARY_TEXT,
        )
    )
    if note:
        parts.append(
            text(
                panel_x + 20,
                162,
                note,
                font_family=FONT_FAMILY,
                font_size="13",
                fill=MUTED_TEXT,
            )
        )
    maximum = max(values.values())
    for index, condition in enumerate(CONDITIONS):
        y = 174 + index * 77
        value = values[condition]
        bar_width = 0 if maximum == 0 else value / maximum * BAR_WIDTH
        parts.extend(
            [
                text(
                    panel_x + 92,
                    y + 25,
                    condition.title(),
                    text_anchor="end",
                    font_family=FONT_FAMILY,
                    font_size="16",
                    font_weight="600",
                    fill=SECONDARY_TEXT,
                ),
                f'<rect x="{panel_x + 110}" y="{y}" width="{bar_width:.1f}" height="34" rx="5" fill="{CONDITION_COLOURS[condition]}"/>',
                text(
                    panel_x + 122 + bar_width,
                    y + 24,
                    f"{value:.2f}{suffix}",
                    font_family=FONT_FAMILY,
                    font_size="16",
                    font_weight="700",
                    fill=SECONDARY_TEXT,
                ),
            ]
        )
