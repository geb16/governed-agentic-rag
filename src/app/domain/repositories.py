"""Domain-owned persistence port for isolated synthetic support state."""

from __future__ import annotations

from typing import Protocol

from app.domain.support import (
    AccessAccountRecord,
    ConsumedFault,
    EscalationRecord,
    FaultPlan,
    RefundRecord,
    SyntheticCaseFixture,
    TicketRecord,
)


class SyntheticRepository(Protocol):
    """Domain port for isolated synthetic support state."""

    def initialize(self) -> None:
        """Create the repository schema when it does not exist."""
        ...

    def create_case(self, fixture: SyntheticCaseFixture, *, replace: bool = False) -> None:
        """Persist a complete isolated case fixture."""
        ...

    def case_exists(self, case_id: str) -> bool:
        """Return whether a case partition exists."""
        ...

    def get_ticket(self, case_id: str, ticket_id: str) -> TicketRecord | None:
        """Read a ticket within one case partition."""
        ...

    def update_ticket_status(
        self, case_id: str, ticket_id: str, new_status: str
    ) -> tuple[TicketRecord | None, bool]:
        """Update ticket status and report whether state changed."""
        ...

    def get_access_account(self, case_id: str, subject_id: str) -> AccessAccountRecord | None:
        """Read an access account within one case partition."""
        ...

    def change_access_role(
        self, case_id: str, subject_id: str, new_role: str
    ) -> tuple[AccessAccountRecord | None, bool]:
        """Change a synthetic role and report whether state changed."""
        ...

    def issue_refund(
        self,
        case_id: str,
        ticket_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> tuple[RefundRecord | None, bool]:
        """Create or return an idempotent synthetic refund."""
        ...

    def request_human_review(
        self,
        case_id: str,
        ticket_id: str,
        reason: str,
        requested_role: str,
        idempotency_key: str,
    ) -> tuple[EscalationRecord | None, bool]:
        """Create or return an idempotent human-review request."""
        ...

    def set_fault_plan(self, case_id: str, plan: FaultPlan) -> None:
        """Replace the deterministic fault plan for a case and tool."""
        ...

    def consume_fault(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        """Consume the next configured failure attempt, if present."""
        ...
