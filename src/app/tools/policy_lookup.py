"""Read-only capability for querying the approved knowledge corpus."""

from __future__ import annotations

from pydantic import Field

from app.domain.schemas import (
    ControlledToolResult,
    EvidenceReference,
    EvidenceType,
    RetrievedChunk,
    StrictModel,
    ToolExecutionContext,
)
from app.rag.retriever import Retriever


class PolicyLookupArguments(StrictModel):
    """Validated policy query and bounded result count."""

    query: str = Field(min_length=3, max_length=500)
    max_results: int = Field(ge=1, le=5)


class PolicyLookupResult(ControlledToolResult):
    """Approved ranked chunks and their evidence references."""

    matches: list[RetrievedChunk]


class PolicyLookupTool:
    """Expose narrower retrieval as a read-only model capability."""

    name = "policy_lookup"
    description = (
        "Search the approved synthetic enterprise knowledge base. Read-only; "
        "use when the initial context is insufficient or a narrower policy search is needed."
    )
    input_model = PolicyLookupArguments

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    def execute(
        self,
        arguments: PolicyLookupArguments,
        context: ToolExecutionContext,
    ) -> PolicyLookupResult:
        """Retrieve approved chunks; trusted case context is intentionally unused."""
        del context
        matches = self._retriever.retrieve(arguments.query, arguments.max_results)
        return PolicyLookupResult(
            message=f"Retrieved {len(matches)} approved knowledge chunks.",
            matches=matches,
            evidence=[
                EvidenceReference(
                    evidence_id=match.chunk_id,
                    evidence_type=EvidenceType.KNOWLEDGE_CHUNK,
                    source_id=match.document_id,
                    title=match.title,
                    content_sha256=match.content_sha256,
                    score=match.score,
                )
                for match in matches
            ],
        )
