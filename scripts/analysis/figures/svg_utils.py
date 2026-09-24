"""Provide deterministic, dependency-free helpers for SVG renderers."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from figures.style import WORD_WIDTH_IN


def word_svg_root(viewbox_width: int, viewbox_height: int) -> str:
    """Create an accessible SVG root sized to the printable width in Word.

    Args:
        viewbox_width: Internal SVG coordinate-system width.
        viewbox_height: Internal SVG coordinate-system height.

    Returns:
        Opening SVG element with a proportional physical size and accessible
        title and description references.

    """
    physical_height = viewbox_height / viewbox_width * WORD_WIDTH_IN
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WORD_WIDTH_IN}in" '
        f'height="{physical_height:.2f}in" viewBox="0 0 {viewbox_width} {viewbox_height}" '
        'role="img" aria-labelledby="title desc">'
    )


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
