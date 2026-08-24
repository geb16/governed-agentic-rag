"""Shared SQLite transaction context for atomic governance state and audit writes."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path

_ActiveSession = tuple[Path, sqlite3.Connection]
_active_session: ContextVar[_ActiveSession | None] = ContextVar(
    "governance_sqlite_session",
    default=None,
)


def normalized_path(database_path: Path) -> Path:
    """Return a stable absolute identity for a SQLite database path."""

    return database_path.resolve()


def active_connection(database_path: Path) -> sqlite3.Connection | None:
    """Return the ambient connection only when it targets the requested database."""

    session = _active_session.get()
    if session is None or session[0] != normalized_path(database_path):
        return None
    return session[1]


def configure_connection(connection: sqlite3.Connection) -> None:
    """Apply the shared safety and concurrency settings to one connection."""

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")


@contextmanager
def sqlite_unit_of_work(database_path: Path) -> Generator[None, None, None]:
    # Commit all repository writes together, joining an existing nested unit.
    if active_connection(database_path) is not None:
        yield
        return

    connection = sqlite3.connect(database_path, timeout=10.0)
    configure_connection(connection)
    connection.execute("BEGIN IMMEDIATE")
    token: Token[_ActiveSession | None] = _active_session.set(
        (normalized_path(database_path), connection)
    )
    try:
        yield
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _active_session.reset(token)
        connection.close()


def begin_immediate(connection: sqlite3.Connection) -> None:
    """Start a write transaction unless an ambient unit already started it."""

    if not connection.in_transaction:
        connection.execute("BEGIN IMMEDIATE")
