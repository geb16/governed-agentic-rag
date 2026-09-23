from __future__ import annotations


def format_value(value: float | None, digits: int = 3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"
