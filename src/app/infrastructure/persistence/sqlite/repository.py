"""Implement the SyntheticRepository port on case-partitioned SQLite.

Facade over the _cases, _records, _actions, and _faults modules. Every method
opens its own connection; state-changing tool operations use BEGIN IMMEDIATE
so concurrent thread-pool requests serialize their writes.
Core:
    - SqliteSyntheticRepository: ticket, account, action, and fault-plan state.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.repositories import SyntheticRepository as SyntheticRepository
from app.domain.support import (
    AccessAccountRecord,
    ConsumedFault,
    EscalationRecord,
    FaultPlan,
    RefundRecord,
    SyntheticCaseFixture,
    TicketRecord,
)
from app.infrastructure.persistence.sqlite import _actions, _cases, _faults, _records
from app.infrastructure.persistence.sqlite.connection import sqlite_connection
from app.infrastructure.persistence.sqlite.schema import initialize_schema


class SqliteSyntheticRepository:
    """SQLite implementation of isolated synthetic business state.

    A fresh connection is used per operation so FastAPI thread-pool invocations do
    not share SQLite connection objects. Every business row is partitioned by
    ``case_id`` to prevent state leakage between evaluation cases.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def initialize(self) -> None:
        """Create the schema and reject incompatible schema versions.

        Raises:
            RuntimeError: If the database records a different schema version.
            sqlite3.Error: If schema initialization fails.
        """
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite_connection(self._database_path) as connection:
            initialize_schema(connection)

    def create_case(self, fixture: SyntheticCaseFixture, *, replace: bool = False) -> None:
        """Insert an isolated case fixture in one transaction.

        Args:
            fixture: Validated tickets, accounts, and fault plans for the case.
            replace: Whether to delete an existing case partition before insertion.
        """
        with sqlite_connection(self._database_path) as connection:
            _cases.create_case(connection, fixture, replace=replace)

    def case_exists(self, case_id: str) -> bool:
        """Return whether the named case partition exists."""
        with sqlite_connection(self._database_path) as connection:
            return _cases.case_exists(connection, case_id)

    def get_ticket(self, case_id: str, ticket_id: str) -> TicketRecord | None:
        """Read one ticket from the specified case partition."""
        with sqlite_connection(self._database_path) as connection:
            return _records.get_ticket(connection, case_id, ticket_id)

    def update_ticket_status(
        self, case_id: str, ticket_id: str, new_status: str
    ) -> tuple[TicketRecord | None, bool]:
        """Update a ticket and increment its version only when status changes."""
        with sqlite_connection(self._database_path, immediate=True) as connection:
            return _records.update_ticket_status(connection, case_id, ticket_id, new_status)

    def get_access_account(self, case_id: str, subject_id: str) -> AccessAccountRecord | None:
        """Read one synthetic access account from a case partition."""
        with sqlite_connection(self._database_path) as connection:
            return _records.get_access_account(connection, case_id, subject_id)

    def change_access_role(
        self, case_id: str, subject_id: str, new_role: str
    ) -> tuple[AccessAccountRecord | None, bool]:
        """Change a synthetic role and increment its version when required."""
        with sqlite_connection(self._database_path, immediate=True) as connection:
            return _records.change_access_role(connection, case_id, subject_id, new_role)

    def issue_refund(
        self,
        case_id: str,
        ticket_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> tuple[RefundRecord | None, bool]:
        """Create an idempotent synthetic refund for an existing case ticket."""
        with sqlite_connection(self._database_path, immediate=True) as connection:
            return _actions.issue_refund(
                connection,
                case_id,
                ticket_id,
                amount_minor,
                currency,
                idempotency_key,
            )

    def request_human_review(
        self,
        case_id: str,
        ticket_id: str,
        reason: str,
        requested_role: str,
        idempotency_key: str,
    ) -> tuple[EscalationRecord | None, bool]:
        """Create an idempotent pending review for an existing case ticket."""
        with sqlite_connection(self._database_path, immediate=True) as connection:
            return _actions.request_human_review(
                connection,
                case_id,
                ticket_id,
                reason,
                requested_role,
                idempotency_key,
            )

    def set_fault_plan(self, case_id: str, plan: FaultPlan) -> None:
        """Replace one case-scoped deterministic tool-failure plan."""
        with sqlite_connection(self._database_path) as connection:
            _faults.set_fault_plan(connection, case_id, plan)

    def consume_fault(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        """Atomically consume and number the next planned failure attempt."""
        with sqlite_connection(self._database_path, immediate=True) as connection:
            return _faults.consume_fault(connection, case_id, tool_name)
