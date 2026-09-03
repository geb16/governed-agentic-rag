"""Shared recording retrieval and isolated SQLite state probes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.evidence import RetrievedChunk
from app.rag.retriever import Retriever

from paired_agent_evaluation.domain.observations import BusinessState, RetrievedEvidence


class RecordingRetriever:
    def __init__(self, inner: Retriever) -> None:
        self._inner = inner
        self.calls: list[list[RetrievedChunk]] = []

    @property
    def backend_name(self) -> str:
        return self._inner.backend_name

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        chunks = self._inner.retrieve(query, top_k)
        self.calls.append(chunks)
        return chunks

    def evidence(self) -> list[RetrievedEvidence]:
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
