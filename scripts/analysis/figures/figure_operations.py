# Rendering operational latency and token indicators.

# ruff: noqa: E501 -- SVG elements remain readable as complete element strings.

from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from figures.svg_utils import text, write_svg


def render_operational_indicators(
    summary: dict[str, Any],
    normalized: list[dict[str, Any]],
    target: Path,
) -> None:
    """Render separate-scale panels for latency and token usage."""

    latency: dict[str, list[float]] = defaultdict(list)
    for row in normalized:
        latency[row["key"]["condition"]].append(float(row["latency_ms"]))
    tokens = summary["token_usage_by_condition"]
    latency_values = {
        condition: statistics.median(latency[condition]) / 1000
        for condition in ("baseline", "governed")
    }
    token_values = {
        condition: (tokens[condition]["input_tokens"] + tokens[condition]["output_tokens"]) / 10000
        for condition in ("baseline", "governed")
    }
    width, height = 1200, 365
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Operational cost indicators</title>',
        '<desc id="desc">Separate panels show median latency in seconds and total token usage in tens of thousands.</desc>',
        '<rect width="100%" height="100%" fill="#fbfcfe"/>',
        text(
            38,
            45,
            "Operational indicators",
            font_family="Arial",
            font_size="24",
            font_weight="700",
            fill="#172554",
        ),
    ]
    panels = [
        (40, "Median latency (seconds)", latency_values, "s"),
        (630, "Total tokens (x10,000)", token_values, ""),
    ]
    for panel_x, title, values, suffix in panels:
        _add_panel(parts, panel_x, title, values, suffix)
    write_svg(target, parts)


def _add_panel(
    parts: list[str],
    panel_x: int,
    title: str,
    values: dict[str, float],
    suffix: str,
) -> None:
    parts.append(
        text(
            panel_x,
            92,
            title,
            font_family="Arial",
            font_size="17",
            font_weight="700",
            fill="#334155",
        )
    )
    maximum = max(values.values())
    for index, condition in enumerate(("baseline", "governed")):
        y = 125 + index * 78
        value = values[condition]
        colour = "#64748b" if condition == "baseline" else "#0f766e"
        bar_width = value / maximum * 350
        parts.extend(
            [
                text(
                    panel_x + 95,
                    y + 23,
                    condition.title(),
                    text_anchor="end",
                    font_family="Arial",
                    font_size="14",
                    fill="#334155",
                ),
                f'<rect x="{panel_x + 115}" y="{y}" width="{bar_width:.1f}" height="35" rx="5" fill="{colour}"/>',
                text(
                    panel_x + 130 + bar_width,
                    y + 24,
                    f"{value:.2f}{suffix}",
                    font_family="Arial",
                    font_size="14",
                    font_weight="700",
                    fill="#0f172a",
                ),
            ]
        )
    parts.append(
        text(
            panel_x + 115,
            305,
            "Panels use independent scales; compare conditions within each panel.",
            font_family="Arial",
            font_size="12",
            fill="#64748b",
        )
    )
