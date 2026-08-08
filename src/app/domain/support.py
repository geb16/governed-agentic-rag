from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.domain.schemas import StrictModel


class FailureMode(StrEnum):
    TRANSIENT_ERROR = "transient_error"
    TIMEOUT = "timeout"
    PERMANENT_ERROR = "permanent_error"


class AccessAccountRecord(StrictModel):
    subject_id: str = Field(pattern=r"^USR-[0-9]{4}$")
    role: str
    version: int = Field(ge=1)


class RefundRecord(StrictModel):
    refund_id: str
    ticket_id: str
    amount_minor: int = Field(gt=0)
    currency: str
    status: str
    idempotency_key: str


class EscalationRecord(StrictModel):
    escalation_id: str
    ticket_id: str
    reason: str
    requested_role: str
    status: str
    idempotency_key: str


class FaultPlan(StrictModel):
    tool_name: str = Field(min_length=1, max_length=100)
    mode: FailureMode
    failures: int = Field(ge=1, le=20)
    error_code: str = Field(min_length=3, max_length=100)


class TicketRecord(StrictModel):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    status: str
    category: str
    summary: str
    version: int = Field(ge=1)


class ConsumedFault(StrictModel):
    mode: FailureMode
    error_code: str
    attempt_number: int = Field(ge=1)

    @property
    def retryable(self) -> bool:
        return self.mode in {FailureMode.TRANSIENT_ERROR, FailureMode.TIMEOUT}


class SyntheticCaseFixture(StrictModel):
    case_id: str = Field(pattern=r"^case_[a-zA-Z0-9_-]+$")
    tickets: list[TicketRecord] = Field(default_factory=list)
    access_accounts: list[AccessAccountRecord] = Field(default_factory=list)
    fault_plans: list[FaultPlan] = Field(default_factory=list)


DEFAULT_CASE_FIXTURE = SyntheticCaseFixture(
    case_id="case_default",
    tickets=[
        TicketRecord(
            ticket_id="TKT-1001",
            status="open",
            category="identity_access",
            summary="Privileged access request awaiting IAM review.",
            version=1,
        ),
        TicketRecord(
            ticket_id="TKT-1002",
            status="resolved",
            category="customer_support",
            summary="Customer identity verification completed.",
            version=1,
        ),
        TicketRecord(
            ticket_id="TKT-1003",
            status="open",
            category="refund",
            summary="Refund request submitted with reason code.",
            version=1,
        ),
    ],
    access_accounts=[
        AccessAccountRecord(subject_id="USR-1001", role="viewer", version=1),
        AccessAccountRecord(subject_id="USR-1002", role="support_agent", version=1),
    ],
)


__all__ = [
    "DEFAULT_CASE_FIXTURE",
    "AccessAccountRecord",
    "ConsumedFault",
    "EscalationRecord",
    "FailureMode",
    "FaultPlan",
    "RefundRecord",
    "SyntheticCaseFixture",
    "TicketRecord",
]
