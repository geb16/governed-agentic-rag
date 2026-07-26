from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.version import DATABASE_SCHEMA_VERSION
from app.persistence.models import (
    AccessAccountRecord,
    ConsumedFault,
    EscalationRecord,
    FaultPlan,
    RefundRecord,
    SyntheticCaseFixture,
    TicketRecord,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS synthetic_cases (
    case_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    case_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    status TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (case_id, ticket_id),
    FOREIGN KEY (case_id) REFERENCES synthetic_cases(case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_accounts (
    case_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    role TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (case_id, subject_id),
    FOREIGN KEY (case_id) REFERENCES synthetic_cases(case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS refunds (
    case_id TEXT NOT NULL,
    refund_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (case_id, refund_id),
    UNIQUE (case_id, idempotency_key),
    FOREIGN KEY (case_id, ticket_id) REFERENCES tickets(case_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS escalations (
    case_id TEXT NOT NULL,
    escalation_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_role TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (case_id, escalation_id),
    UNIQUE (case_id, idempotency_key),
    FOREIGN KEY (case_id, ticket_id) REFERENCES tickets(case_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS fault_plans (
    case_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    mode TEXT NOT NULL,
    failures_remaining INTEGER NOT NULL,
    failures_consumed INTEGER NOT NULL DEFAULT 0,
    error_code TEXT NOT NULL,
    PRIMARY KEY (case_id, tool_name),
    FOREIGN KEY (case_id) REFERENCES synthetic_cases(case_id) ON DELETE CASCADE
);
"""

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

class SqliteSyntheticRepository:
    """SQLite implementation of isolated synthetic business state.

    A fresh connection is used per operation so FastAPI thread-pool invocations do
    not share SQLite connection objects. Every business row is partitioned by
    ``case_id`` to prevent state leakage between evaluation cases.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(_SCHEMA)
            existing = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if existing is not None and int(existing["value"]) != DATABASE_SCHEMA_VERSION:
                raise RuntimeError(
                    "Unsupported synthetic database schema version "
                    f"{existing['value']}; expected {DATABASE_SCHEMA_VERSION}"
                )
            connection.execute(
                """
                INSERT INTO schema_metadata(key, value) VALUES ('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(DATABASE_SCHEMA_VERSION),),
            )

    def create_case(self, fixture: SyntheticCaseFixture, *, replace: bool = False) -> None:
        with self._connect() as connection:
            if replace:
                connection.execute(
                    "DELETE FROM synthetic_cases WHERE case_id = ?", (fixture.case_id,)
                )
            connection.execute(
                "INSERT INTO synthetic_cases(case_id, created_at) VALUES (?, ?)",
                (fixture.case_id, datetime.now(UTC).isoformat()),
            )
            connection.executemany(
                """
                INSERT INTO tickets(case_id, ticket_id, status, category, summary, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        fixture.case_id,
                        ticket.ticket_id,
                        ticket.status,
                        ticket.category,
                        ticket.summary,
                        ticket.version,
                    )
                    for ticket in fixture.tickets
                ],
            )
            connection.executemany(
                """
                INSERT INTO access_accounts(case_id, subject_id, role, version)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        fixture.case_id,
                        account.subject_id,
                        account.role,
                        account.version,
                    )
                    for account in fixture.access_accounts
                ],
            )
            for plan in fixture.fault_plans:
                self._set_fault_plan(connection, fixture.case_id, plan)
    
    def case_exists(self, case_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM synthetic_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return row is not None

    def get_ticket(self, case_id: str, ticket_id: str) -> TicketRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT ticket_id, status, category, summary, version
                FROM tickets WHERE case_id = ? AND ticket_id = ?
                """,
                (case_id, ticket_id),
            ).fetchone()
        return self._ticket_from_row(row)

    
    @staticmethod
    def _ticket_from_row(row: sqlite3.Row | None) -> TicketRecord | None:
        if row is None:
            return None
        return TicketRecord.model_validate(dict(row))