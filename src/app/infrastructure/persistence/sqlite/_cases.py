"""SQLite operations for synthetic evaluation-case partitions."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app.domain.support import SyntheticCaseFixture
from app.infrastructure.persistence.sqlite._faults import upsert_fault_plan


def create_case(
    connection: sqlite3.Connection,
    fixture: SyntheticCaseFixture,
    *,
    replace: bool,
) -> None:
    """Persist one complete case fixture using the caller-owned transaction."""

    if replace:
        connection.execute(
            "DELETE FROM synthetic_cases WHERE case_id = ?",
            (fixture.case_id,),
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
        upsert_fault_plan(connection, fixture.case_id, plan)


def case_exists(connection: sqlite3.Connection, case_id: str) -> bool:
    """Return whether a synthetic case partition exists."""

    row = connection.execute(
        "SELECT 1 FROM synthetic_cases WHERE case_id = ?",
        (case_id,),
    ).fetchone()
    return row is not None
