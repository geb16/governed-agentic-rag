"""SQLite adapter for case-partitioned synthetic support-domain state."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.core.version import DATABASE_SCHEMA_VERSION
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
        """Create the schema and reject incompatible schema versions.

        Raises:
            RuntimeError: If the database records a different schema version.
            sqlite3.Error: If schema initialization fails.
        """
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
        """Insert an isolated case fixture in one transaction.

        Args:
            fixture: Validated tickets, accounts, and fault plans for the case.
            replace: Whether to delete an existing case partition before insertion.
        """
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
        """Return whether the named case partition exists."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM synthetic_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return row is not None

    def get_ticket(self, case_id: str, ticket_id: str) -> TicketRecord | None:
        """Read one ticket from the specified case partition."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT ticket_id, status, category, summary, version
                FROM tickets WHERE case_id = ? AND ticket_id = ?
                """,
                (case_id, ticket_id),
            ).fetchone()
        return self._ticket_from_row(row)

    def update_ticket_status(
        self, case_id: str, ticket_id: str, new_status: str
    ) -> tuple[TicketRecord | None, bool]:
        """Update a ticket and increment its version only when status changes."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM tickets WHERE case_id = ? AND ticket_id = ?",
                (case_id, ticket_id),
            ).fetchone()
            if row is None:
                return None, False
            changed = row["status"] != new_status
            if changed:
                connection.execute(
                    """
                    UPDATE tickets SET status = ?, version = version + 1
                    WHERE case_id = ? AND ticket_id = ?
                    """,
                    (new_status, case_id, ticket_id),
                )
            updated = connection.execute(
                """
                SELECT ticket_id, status, category, summary, version
                FROM tickets WHERE case_id = ? AND ticket_id = ?
                """,
                (case_id, ticket_id),
            ).fetchone()
        return self._ticket_from_row(updated), changed

    def get_access_account(self, case_id: str, subject_id: str) -> AccessAccountRecord | None:
        """Read one synthetic access account from a case partition."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT subject_id, role, version FROM access_accounts
                WHERE case_id = ? AND subject_id = ?
                """,
                (case_id, subject_id),
            ).fetchone()
        return self._access_from_row(row)

    def change_access_role(
        self, case_id: str, subject_id: str, new_role: str
    ) -> tuple[AccessAccountRecord | None, bool]:
        """Change a synthetic role and increment its version when required."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT role FROM access_accounts WHERE case_id = ? AND subject_id = ?",
                (case_id, subject_id),
            ).fetchone()
            if row is None:
                return None, False
            changed = row["role"] != new_role
            if changed:
                connection.execute(
                    """
                    UPDATE access_accounts SET role = ?, version = version + 1
                    WHERE case_id = ? AND subject_id = ?
                    """,
                    (new_role, case_id, subject_id),
                )
            updated = connection.execute(
                """
                SELECT subject_id, role, version FROM access_accounts
                WHERE case_id = ? AND subject_id = ?
                """,
                (case_id, subject_id),
            ).fetchone()
        return self._access_from_row(updated), changed

    def issue_refund(
        self,
        case_id: str,
        ticket_id: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
    ) -> tuple[RefundRecord | None, bool]:
        """Create an idempotent synthetic refund for an existing case ticket."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT refund_id, ticket_id, amount_minor, currency, status, idempotency_key
                FROM refunds WHERE case_id = ? AND idempotency_key = ?
                """,
                (case_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return self._refund_from_row(existing), False
            ticket = connection.execute(
                "SELECT 1 FROM tickets WHERE case_id = ? AND ticket_id = ?",
                (case_id, ticket_id),
            ).fetchone()
            if ticket is None:
                return None, False
            refund_id = f"RFD-{uuid4().hex[:12].upper()}"
            connection.execute(
                """
                INSERT INTO refunds(
                    case_id, refund_id, ticket_id, amount_minor, currency, status,
                    idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, 'simulated_issued', ?, ?)
                """,
                (
                    case_id,
                    refund_id,
                    ticket_id,
                    amount_minor,
                    currency,
                    idempotency_key,
                    datetime.now(UTC).isoformat(),
                ),
            )
            row = connection.execute(
                """
                SELECT refund_id, ticket_id, amount_minor, currency, status, idempotency_key
                FROM refunds WHERE case_id = ? AND refund_id = ?
                """,
                (case_id, refund_id),
            ).fetchone()
        return self._refund_from_row(row), True

    def request_human_review(
        self,
        case_id: str,
        ticket_id: str,
        reason: str,
        requested_role: str,
        idempotency_key: str,
    ) -> tuple[EscalationRecord | None, bool]:
        """Create an idempotent pending review for an existing case ticket."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT escalation_id, ticket_id, reason, requested_role, status, idempotency_key
                FROM escalations WHERE case_id = ? AND idempotency_key = ?
                """,
                (case_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return self._escalation_from_row(existing), False
            ticket = connection.execute(
                "SELECT 1 FROM tickets WHERE case_id = ? AND ticket_id = ?",
                (case_id, ticket_id),
            ).fetchone()
            if ticket is None:
                return None, False
            escalation_id = f"ESC-{uuid4().hex[:12].upper()}"
            connection.execute(
                """
                INSERT INTO escalations(
                    case_id, escalation_id, ticket_id, reason, requested_role, status,
                    idempotency_key, created_at
                ) VALUES (?, ?, ?, ?, ?, 'pending_human_review', ?, ?)
                """,
                (
                    case_id,
                    escalation_id,
                    ticket_id,
                    reason,
                    requested_role,
                    idempotency_key,
                    datetime.now(UTC).isoformat(),
                ),
            )
            row = connection.execute(
                """
                SELECT escalation_id, ticket_id, reason, requested_role, status, idempotency_key
                FROM escalations WHERE case_id = ? AND escalation_id = ?
                """,
                (case_id, escalation_id),
            ).fetchone()
        return self._escalation_from_row(row), True

    def set_fault_plan(self, case_id: str, plan: FaultPlan) -> None:
        """Replace one case-scoped deterministic tool-failure plan."""
        with self._connect() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM synthetic_cases WHERE case_id = ?", (case_id,)
                ).fetchone()
                is None
            ):
                raise KeyError(f"Unknown synthetic case: {case_id}")
            self._set_fault_plan(connection, case_id, plan)

    @staticmethod
    def _set_fault_plan(connection: sqlite3.Connection, case_id: str, plan: FaultPlan) -> None:
        connection.execute(
            """
            INSERT INTO fault_plans(
                case_id, tool_name, mode, failures_remaining, failures_consumed, error_code
            ) VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(case_id, tool_name) DO UPDATE SET
                mode = excluded.mode,
                failures_remaining = excluded.failures_remaining,
                failures_consumed = 0,
                error_code = excluded.error_code
            """,
            (case_id, plan.tool_name, plan.mode.value, plan.failures, plan.error_code),
        )

    def consume_fault(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        """Atomically consume and number the next planned failure attempt."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT mode, failures_remaining, failures_consumed, error_code
                FROM fault_plans WHERE case_id = ? AND tool_name = ?
                """,
                (case_id, tool_name),
            ).fetchone()
            if row is None or int(row["failures_remaining"]) <= 0:
                return None
            attempt_number = int(row["failures_consumed"]) + 1
            connection.execute(
                """
                UPDATE fault_plans
                SET failures_remaining = failures_remaining - 1,
                    failures_consumed = failures_consumed + 1
                WHERE case_id = ? AND tool_name = ?
                """,
                (case_id, tool_name),
            )
        return ConsumedFault(
            mode=row["mode"],
            error_code=row["error_code"],
            attempt_number=attempt_number,
        )

    @staticmethod
    def _ticket_from_row(row: sqlite3.Row | None) -> TicketRecord | None:
        if row is None:
            return None
        return TicketRecord.model_validate(dict(row))

    @staticmethod
    def _access_from_row(row: sqlite3.Row | None) -> AccessAccountRecord | None:
        if row is None:
            return None
        return AccessAccountRecord.model_validate(dict(row))

    @staticmethod
    def _refund_from_row(row: sqlite3.Row | None) -> RefundRecord | None:
        if row is None:
            return None
        return RefundRecord.model_validate(dict(row))

    @staticmethod
    def _escalation_from_row(row: sqlite3.Row | None) -> EscalationRecord | None:
        if row is None:
            return None
        return EscalationRecord.model_validate(dict(row))
