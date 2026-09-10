"""Render a deterministic, self-contained HTML view of primary results."""

from __future__ import annotations

from typing import Any



def render_html_report(
    summary: dict[str, Any],
    estimates: list[dict[str, Any]],
    differences: list[dict[str, Any]],
) -> str:
    # TODO: Rendering primary JSON results as an accessible standalone HTML report.
    return f"""<!doctype html>"