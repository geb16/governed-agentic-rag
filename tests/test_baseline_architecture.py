from __future__ import annotations

from pathlib import Path
from typing import Any

from app.baseline.agent import BaselineAgent
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.schemas import (
    BaselineRequest,
    ModelTurn,
    RetrievedChunk,
)

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

class FakeModel:
    model_name = "fake-model"

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = turns
        self.calls = 0

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        self.calls += 1
        return self._turns.pop(0)

def _request() -> BaselineRequest:
    return BaselineRequest(
        case_id="case_default",
        requester_id="requester-1",
        query="Explain the refund policy",
    )


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-refund",
        document_id="refund-policy",
        title="Refund policy",
        content="Refunds require an eligible ticket.",
        source_path="refund_policy.md",
        score=0.9,
        content_sha256="a" * 64,
    )

def _agent(
    *,
    model: FakeModel,
    repository: FakeRepository | None = None,
    tool_router: ToolRouter | None = None,
) -> BaselineAgent:
    return BaselineAgent(
        settings=Settings(),
        retriever=FakeRetriever([_chunk()]),  # type: ignore[arg-type]
        model=model,
        tool_router=tool_router or ToolRouter([]),
        repository=repository or FakeRepository(),  # type: ignore[arg-type]
    )

