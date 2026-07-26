from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
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