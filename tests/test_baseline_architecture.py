from __future__ import annotations

from pathlib import Path

from app.domain.schemas import RetrievedChunk

SOURCE_ROOT = Path(__file__).parents[1] / "src" / "app"


class FakeRepository:
    def __init__(self, *, case_exists: bool = True) -> None:
        self._case_exists = case_exists

    def case_exists(self, case_id: str) -> bool:
        return self._case_exists

class FakeRetriever:
    backend_name = "fake"

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        return self._chunks
