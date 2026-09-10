"""Records retrieval evidence and snapshots isolated SQLite business state.

References:
    [1] Python, "sqlite3 — DB-API 2.0 interface for SQLite databases."
        https://docs.python.org/3/library/sqlite3.html
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.evidence import RetrievedChunk
from app.rag.retriever import Retriever

from paired_agent_evaluation.domain.observations import BusinessState, RetrievedEvidence


class RecordingRetriever:
    """Decorates a retriever while recording successful retrieval results."""

    def __init__(self, inner: Retriever) -> None:
        self._inner = inner
        self.calls: list[list[RetrievedChunk]] = []

    @property
    def backend_name(self) -> str:
        """Returns the wrapped retriever's backend name."""
        return self._inner.backend_name

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Delegates retrieval and records the returned chunks."""
        chunks = self._inner.retrieve(query, top_k)
        self.calls.append(chunks)
        return chunks

    def evidence(self) -> list[RetrievedEvidence]:
        """Returns recorded evidence deduplicated by chunk identity.

        Chunk order follows first appearance across successful calls. If a chunk
        appears again, its most recently returned values replace the earlier ones.
        """
        unique: dict[str, RetrievedChunk] = {}
        for call in self.calls:
            unique.update((chunk.chunk_id, chunk) for chunk in call)
        return [
            RetrievedEvidence(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                content=chunk.content,
                content_sha256=chunk.content_sha256,
                score=chunk.score,
            )
            for chunk in unique.values()
        ]


def state_snapshot(database_path: Path, case_id: str) -> BusinessState:
    """Loads a deterministic business-state snapshot for one case.

    Rows from each experiment-owned table are selected with a bound case ID and
    stable ordering. Volatile ``created_at`` values are excluded before the
    result is validated as ``BusinessState``.

    Args:
        database_path: SQLite database produced by an isolated execution.
        case_id: Evaluation case whose records should be selected.

    Returns:
        Validated ticket, account, refund, and escalation state.
    """
    tables = {
        "tickets": ("ticket_id",),
        "access_accounts": ("subject_id",),
        "refunds": ("refund_id",),
        "escalations": ("escalation_id",),
    }
    values: dict[str, list[dict[str, object]]] = {}
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        for table, order in tables.items():
            ordering = ", ".join(order)
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE case_id = ? ORDER BY {ordering}",
                (case_id,),
            ).fetchall()
            values[table] = [
                {key: row[key] for key in row.keys() if key not in {"created_at"}} for row in rows
            ]
    return BusinessState.model_validate(values)
