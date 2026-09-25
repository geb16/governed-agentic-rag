"""Open one transactional SQLite connection per repository operation.

Each connection enforces foreign keys, waits on locks for a bounded time, and
returns sqlite3.Row rows; immediate=True takes the write lock up front. Commits
on success, rolls back on error, and always closes, so threads never share one.
Core:
    - sqlite_connection: context manager owning one connection's transaction.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

SQLITE_TIMEOUT_SECONDS = 10.0
SQLITE_BUSY_TIMEOUT_MS = 10_000


@contextmanager
def sqlite_connection(
    database_path: Path,
    *,
    immediate: bool = False,
) -> Generator[sqlite3.Connection, None, None]:
    """Open one configured SQLite connection and own its transaction lifecycle.

    A new connection is created for each repository operation so worker threads never
    share connection objects. Foreign-key enforcement and bounded lock waiting are
    enabled consistently. Successful operations commit; exceptions roll back before
    the connection is closed.

    Args:
        database_path: Filesystem path of the SQLite database.
        immediate: Whether to acquire the SQLite write reservation before yielding.

    Yields:
        A row-aware SQLite connection scoped to one repository operation.

    Raises:
        sqlite3.Error: If the connection, transaction, or close operation fails.
    """

    connection = sqlite3.connect(database_path, timeout=SQLITE_TIMEOUT_SECONDS)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        if immediate:
            connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


__all__ = ["sqlite_connection"]
