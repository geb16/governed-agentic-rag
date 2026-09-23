# helpers shared by the dependency-free SVG renderers.

from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def format_value(value: float | None, digits: int = 3) -> str:
    """Format a metric value, retaining an explicit non-estimable marker."""

    return "NA" if value is None else f"{value:.{digits}f}"


def text(x: float, y: float, value: str, **attrs: Any) -> str:
    """Render an escaped SVG text element."""

    attributes = " ".join(
        f'{key.replace("_", "-")}="{html.escape(str(item))}"' for key, item in attrs.items()
    )
    return f'<text x="{x}" y="{y}" {attributes}>{html.escape(value)}</text>'


def write_svg(target: Path, parts: list[str]) -> None:
    """Write SVG elements with deterministic line endings."""

    target.write_text("\n".join([*parts, "</svg>"]) + "\n", encoding="utf-8")
