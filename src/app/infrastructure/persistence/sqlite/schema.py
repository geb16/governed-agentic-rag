"""Define and initialize the versioned synthetic support schema.

Every business table is partitioned by case_id and linked by foreign keys;
refunds and escalations are unique per (case_id, idempotency_key).
initialize_schema enables WAL, creates tables idempotently, and rejects a
database stamped with a different DATABASE_SCHEMA_VERSION.
Core:
    - SUPPORT_SCHEMA_SQL: DDL for all synthetic support tables.
    - initialize_schema: creates the schema and checks its version.
"""

from __future__ import annotations

import sqlite3

from app.core.version import DATABASE_SCHEMA_VERSION

SUPPORT_SCHEMA_SQL = """
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


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the support schema and reject an incompatible stored version.

    Args:
        connection: Caller-owned connection used for schema initialization.

    Raises:
        RuntimeError: If the database contains a different schema version.
        sqlite3.Error: If SQLite cannot initialize or inspect the schema.
    """

    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(SUPPORT_SCHEMA_SQL)
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


__all__ = ["SUPPORT_SCHEMA_SQL", "initialize_schema"]
