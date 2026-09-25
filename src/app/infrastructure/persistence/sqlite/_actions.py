"""Persist idempotent simulated refunds and human-review requests.

Each action is keyed by (case_id, idempotency_key): a repeat returns the stored
record without writing, and an unknown ticket returns None. Results are
(record, created) tuples; statuses are simulated and nothing leaves SQLite.
Core:
    - issue_refund: creates or replays a simulated refund.
    - request_human_review: creates or replays a pending review request.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.support import EscalationRecord, RefundRecord


def issue_refund(
    connection: sqlite3.Connection,
    case_id: str,
    ticket_id: str,
    amount_minor: int,
    currency: str,
    idempotency_key: str,
) -> tuple[RefundRecord | None, bool]:
    """Create or return an idempotent synthetic refund."""

    existing = connection.execute(
        """
        SELECT refund_id, ticket_id, amount_minor, currency, status, idempotency_key
        FROM refunds WHERE case_id = ? AND idempotency_key = ?
        """,
        (case_id, idempotency_key),
    ).fetchone()
    if existing is not None:
        return _refund_from_row(existing), False
    if not _ticket_exists(connection, case_id, ticket_id):
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
    return _refund_from_row(row), True


def request_human_review(
    connection: sqlite3.Connection,
    case_id: str,
    ticket_id: str,
    reason: str,
    requested_role: str,
    idempotency_key: str,
) -> tuple[EscalationRecord | None, bool]:
    """Create or return an idempotent synthetic human-review request."""

    existing = connection.execute(
        """
        SELECT escalation_id, ticket_id, reason, requested_role, status, idempotency_key
        FROM escalations WHERE case_id = ? AND idempotency_key = ?
        """,
        (case_id, idempotency_key),
    ).fetchone()
    if existing is not None:
        return _escalation_from_row(existing), False
    if not _ticket_exists(connection, case_id, ticket_id):
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
    return _escalation_from_row(row), True


def _ticket_exists(connection: sqlite3.Connection, case_id: str, ticket_id: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM tickets WHERE case_id = ? AND ticket_id = ?",
            (case_id, ticket_id),
        ).fetchone()
        is not None
    )


def _refund_from_row(row: sqlite3.Row | None) -> RefundRecord | None:
    if row is None:
        return None
    return RefundRecord.model_validate(dict(row))


def _escalation_from_row(row: sqlite3.Row | None) -> EscalationRecord | None:
    if row is None:
        return None
    return EscalationRecord.model_validate(dict(row))
