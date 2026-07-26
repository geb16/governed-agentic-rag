from __future__ import annotations

from typing import Protocol

from app.persistence.models import (
    AccessAccountRecord,
    ConsumedFault,
    EscalationRecord,
    FaultPlan,
    RefundRecord,
    SyntheticCaseFixture,
    TicketRecord,
)


class SyntheticRepository(Protocol):
    def initialize(self) -> None: ...

    def create_case(self, fixture: SyntheticCaseFixture, *, replace: bool = False) -> None: ...

    def case_exists(self, case_id: str) -> bool: ...

    def get_ticket(self, case_id: str, ticket_id: str) -> TicketRecord | None: ...

    def update_ticket_status(
        self, case_id: str, ticket_id: str, new_status: str
    ) -> tuple[TicketRecord | None, bool]: ...

    def get_access_account(self, case_id: str, subject_id: str) -> AccessAccountRecord | None: ...

    def change_access_role(
        self, case_id: str, subject_id: str, new_role: str
    ) -> tuple[AccessAccountRecord | None, bool]: ...

    def issue_refund(
        self,
        case_id: str,
        ticket_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> tuple[RefundRecord | None, bool]: ...

    def request_human_review(
        self,
        case_id: str,
        ticket_id: str,
        reason: str,
        requested_role: str,
        idempotency_key: str,
    ) -> tuple[EscalationRecord | None, bool]: ...

    def set_fault_plan(self, case_id: str, plan: FaultPlan) -> None: ...

    def consume_fault(self, case_id: str, tool_name: str) -> ConsumedFault | None: ...
