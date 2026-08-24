"""Create SQLite connections that participate in an ambient unit of work.

Standalone operations own commit, rollback, and close behavior. Operations invoked
inside ``SqliteGovernanceUnitOfWork`` reuse its active connection so workflow and
audit writes share one transaction.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from app.audit.sqlite.transaction import active_connection, configure_connection


class SqliteConnectionFactory:
    """Open configured SQLite connections or reuse the active transaction.

    Args:
        database_path: Path identifying the shared pilot database.

    Attributes:
        database_path: Normalized path used to locate an ambient transaction.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize the factory for one resolved SQLite database path."""
        self.database_path = database_path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a configured connection with explicit transaction ownership.

        Yields:
            An ambient connection when inside a unit of work; otherwise a newly
            opened connection that commits on success and rolls back on failure.

        Raises:
            sqlite3.Error: If connection, commit, rollback, or close fails.
            Exception: Re-raises any caller exception after rolling back an owned
                connection.
        """
        ambient = active_connection(self.database_path)
        if ambient is not None:
            yield ambient
            return
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        configure_connection(connection)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
