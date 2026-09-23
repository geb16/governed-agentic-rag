"""Provide shared display formatting for Phase 7 tables and figures."""

from __future__ import annotations


def format_value(value: float | None, digits: int = 3) -> str:
    """Format an optional numeric result for publication output.

    Args:
        value: Numeric value to format, or ``None`` for an unavailable result.
        digits: Number of digits to retain after the decimal point.

    Returns:
        The fixed-precision value, or ``"NA"`` when no value is available.

    """
    return "NA" if value is None else f"{value:.{digits}f}"
