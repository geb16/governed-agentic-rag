"""Factories that keep hand-authored scenario modules concise and consistent."""

from __future__ import annotations

from typing import Any

from app.domain.support import (
    FailureMode,
    FaultPlan,
)


def fault(tool_name: str, mode: str, failures: int, code: str) -> FaultPlan:
    """Create a bounded deterministic failure fixture."""
    return FaultPlan(
        tool_name=tool_name,
        mode=FailureMode(mode),
        failures=failures,
        error_code=code,
    )



def refund_arguments(number: int, amount_minor: int, currency: str = "GBP") -> dict[str, Any]:
    """Create exact valid arguments with a stable idempotency key."""
    return {
        "ticket_id": "TKT-1001",
        "amount_minor": amount_minor,
        "currency": currency,
        "idempotency_key": f"eval{number:04d}refund",
    }


def review_arguments(number: int, role: str, reason: str) -> dict[str, Any]:
    """Create an exact synthetic escalation payload."""
    return {
        "ticket_id": "TKT-1001",
        "reason": reason,
        "requested_role": role,
        "idempotency_key": f"eval{number:04d}review",
    }
