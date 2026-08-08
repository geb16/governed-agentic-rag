from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.application.baseline.ports import ToolExecution
from app.domain.schemas import (
    Citation,
    EvidenceReference,
    EvidenceType,
    ModelTurn,
    RetrievedChunk,
    ToolCallRecord,
    Usage,
)


@dataclass(slots=True)
class InvocationState:
    """Mutable state for one invocation; never shared between requests."""

    input_items: list[dict[str, Any]]
    available_chunks: dict[str, RetrievedChunk]
    available_evidence: dict[str, EvidenceReference]
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @classmethod
    def from_retrieval(
        cls,
        *,
        user_prompt: str,
        chunks: list[RetrievedChunk],
    ) -> InvocationState:
        return cls(
            input_items=[{"role": "user", "content": user_prompt}],
            available_chunks={chunk.chunk_id: chunk for chunk in chunks},
            available_evidence={
                chunk.chunk_id: EvidenceReference(
                    evidence_id=chunk.chunk_id,
                    evidence_type=EvidenceType.KNOWLEDGE_CHUNK,
                    source_id=chunk.document_id,
                    title=chunk.title,
                    content_sha256=chunk.content_sha256,
                    score=chunk.score,
                )
                for chunk in chunks
            },
        )

    @property
    def usage(self) -> Usage:
        return Usage(input_tokens=self.input_tokens, output_tokens=self.output_tokens)

    def record_model_turn(self, turn: ModelTurn) -> None:
        self.input_tokens += turn.input_tokens
        self.output_tokens += turn.output_tokens

    def record_tool_execution(self, turn: ModelTurn, execution: ToolExecution) -> None:
        self.tool_calls.append(execution.record)
        self.available_chunks.update(
            (chunk.chunk_id, chunk) for chunk in execution.retrieved_chunks
        )
        self.available_evidence.update(
            (item.evidence_id, item) for item in execution.record.evidence
        )
        self.input_items.extend(turn.continuation_items)
        self.input_items.append(
            {
                "type": "function_call_output",
                "call_id": execution.record.call_id,
                "output": execution.output_json,
            }
        )

    def citations_for(self, chunk_ids: list[str]) -> list[Citation]:
        return [
            Citation(
                chunk_id=chunk_id,
                document_id=self.available_chunks[chunk_id].document_id,
                title=self.available_chunks[chunk_id].title,
                score=self.available_chunks[chunk_id].score,
            )
            for chunk_id in chunk_ids
        ]

    def evidence_for(self, chunk_ids: list[str]) -> list[EvidenceReference]:
        evidence = [self.available_evidence[chunk_id] for chunk_id in chunk_ids]
        seen_ids = {item.evidence_id for item in evidence}
        for record in self.tool_calls:
            for item in record.evidence:
                if item.evidence_id not in seen_ids:
                    evidence.append(item)
                    seen_ids.add(item.evidence_id)
        return evidence
