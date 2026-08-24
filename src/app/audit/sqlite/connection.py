from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from app.audit.sqlite.transaction import active_connection, configure_connection


class AuditConnectionFactory:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
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
