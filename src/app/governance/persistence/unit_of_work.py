"""Provide the concrete transaction boundary for Phase 4 persistence.

The workflow and keyed audit repositories share one SQLite database and ambient
connection, ensuring required audit events commit or roll back with state changes.
"""

from contextlib import AbstractContextManager
from pathlib import Path

from app.audit.sqlite.transaction import sqlite_unit_of_work


class SqliteGovernanceUnitOfWork:
    """Coordinate workflow and audit repositories on one SQLite transaction.

    Args:
        database_path: Shared database path used to bind the ambient connection.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize the unit of work for the shared SQLite database path."""
        self._database_path = database_path

    def transaction(self) -> AbstractContextManager[None]:
        """Return a transaction joined by both SQLite repository adapters.

        Returns:
            A context manager that commits all joined writes on success and rolls
            them back together when an exception escapes.
        """
        return sqlite_unit_of_work(self._database_path)
