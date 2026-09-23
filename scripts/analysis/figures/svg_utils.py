"""Provide deterministic, dependency-free helpers for SVG renderers."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def text(x: float, y: float, value: str, **attrs: Any) -> str:
    """Render an escaped SVG text element.

    Args:
        x: Horizontal text coordinate.
        y: Vertical text coordinate.
        value: Text content to escape and render.
        **attrs: SVG attributes; underscores are converted to hyphens.

    Returns:
        A complete SVG ``text`` element.

    """
    attributes = " ".join(
        f'{key.replace("_", "-")}="{html.escape(str(item))}"' for key, item in attrs.items()
    )
    return f'<text x="{x}" y="{y}" {attributes}>{html.escape(value)}</text>'


def write_svg(target: Path, parts: list[str]) -> None:
    """Write SVG elements with deterministic line endings.

    Args:
        target: Destination path for the SVG document.
        parts: Opening SVG element and body elements, excluding its closing tag.

    """
    target.write_text("\n".join([*parts, "</svg>"]) + "\n", encoding="utf-8")
