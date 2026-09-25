"""Read and update versioned ticket and access-account records.

Updates return (record, changed) and increment version only when the value
actually changes, so repeated identical writes are no-ops.
Core:
    - get_ticket, update_ticket_status: case-scoped ticket access.
    - get_access_account, change_access_role: case-scoped account access.
"""

from __future__ import annotations

import sqlite3

from app.domain.support import AccessAccountRecord, TicketRecord


def get_ticket(
    connection: sqlite3.Connection,
    case_id: str,
    ticket_id: str,
) -> TicketRecord | None:
    """Read one ticket from its case partition."""

    row = connection.execute(
        """
        SELECT ticket_id, status, category, summary, version
        FROM tickets WHERE case_id = ? AND ticket_id = ?
        """,
        (case_id, ticket_id),
    ).fetchone()
    return _ticket_from_row(row)


def update_ticket_status(
    connection: sqlite3.Connection,
    case_id: str,
    ticket_id: str,
    new_status: str,
) -> tuple[TicketRecord | None, bool]:
    """Update a ticket status and report whether its version changed."""

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
    return get_ticket(connection, case_id, ticket_id), changed


def get_access_account(
    connection: sqlite3.Connection,
    case_id: str,
    subject_id: str,
) -> AccessAccountRecord | None:
    """Read one access account from its case partition."""

    row = connection.execute(
        """
        SELECT subject_id, role, version FROM access_accounts
        WHERE case_id = ? AND subject_id = ?
        """,
        (case_id, subject_id),
    ).fetchone()
    return _access_from_row(row)


def change_access_role(
    connection: sqlite3.Connection,
    case_id: str,
    subject_id: str,
    new_role: str,
) -> tuple[AccessAccountRecord | None, bool]:
    """Change an account role and report whether its version changed."""

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
    return get_access_account(connection, case_id, subject_id), changed


def _ticket_from_row(row: sqlite3.Row | None) -> TicketRecord | None:
    if row is None:
        return None
    return TicketRecord.model_validate(dict(row))


def _access_from_row(row: sqlite3.Row | None) -> AccessAccountRecord | None:
    if row is None:
        return None
    return AccessAccountRecord.model_validate(dict(row))
