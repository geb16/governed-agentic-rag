"""Factories that keep hand-authored scenario modules concise and consistent."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.domain.support import (
    FailureMode,
    FaultPlan,
)
from app.evaluation.dataset.enums import (
    ExpectedRiskLevel,
    ExpectedRoute,
    ExpectedSensitivity,
    ExpectedTaskType,
    InteractionChannel,
    RecoveryExpectation,
    ScenarioCategory,
)
from app.evaluation.dataset.models import (
    EvaluationCase,
)

_VALIDATION_NUMBERS = {1, 2, 3, 4, 18, 19, 20, 34, 35, 36, 51, 52, 53, 68, 69, 70, 85, 86, 87, 88}
_CHANNELS = tuple(InteractionChannel)


def fault(tool_name: str, mode: str, failures: int, code: str) -> FaultPlan:
    """Create a bounded deterministic failure fixture."""
    return FaultPlan(
        tool_name=tool_name,
        mode=FailureMode(mode),
        failures=failures,
        error_code=code,
    )


def make_case(
    number: int,
    category: ScenarioCategory,
    title: str,
    query: str,
    *,
    route: ExpectedRoute,
    intent: str,
    task_type: ExpectedTaskType,
    sensitivity: ExpectedSensitivity,
    risk: ExpectedRiskLevel,
    tool: str | None = None,
    arguments: dict[str, Any] | None = None,
    approval_roles: Sequence[str] = (),
    human_decisions: Sequence[tuple[str, str]] = (),
    clarification_fields: Sequence[str] = (),
    denial_code: str | None = None,
    documents: Sequence[str] = (),
    risk_flags: Sequence[str] = (),
    tags: Sequence[str] = (),
    pair: str | None = None,
    ticket_status: str | None = None,
    ticket_category: str = "customer_support",
    ticket_summary: str = "Synthetic support request awaiting handling.",
    account_role: str | None = None,
    fault_plans: Sequence[FaultPlan] = (),
    recovery: RecoveryExpectation = RecoveryExpectation.NOT_APPLICABLE,
    attempts: int = 0,
    error_code: str | None = None,
    state_change: bool = False,
    sources: Sequence[str] = ("nist-ai-rmf", "openai-contextual-evals"),
) -> EvaluationCase:
    pass 

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
