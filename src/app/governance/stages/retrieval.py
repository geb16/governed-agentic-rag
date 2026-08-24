"""Implement stage two: policy-aware knowledge retrieval.

Classification selects a deterministic policy route and query enrichment. Retrieved
chunks are converted into content-hashed evidence references used by later proposal,
grounding, audit, and evaluation boundaries.
"""

from __future__ import annotations

from app.domain.evidence import EvidenceReference, EvidenceType
from app.governance.contracts import ClassificationResult, GovernedRequest, RetrievalResult
from app.rag.retriever import Retriever

_ROUTES: dict[str, tuple[str, str]] = {
    "refund": ("refund_policy", "refund approval threshold finance fraud"),
    "access_change": (
        "identity_access_policy",
        "privileged access role IAM approval expiry",
    ),
    "data_deletion": (
        "data_governance_policy",
        "data deletion DPO approval legal hold audit",
    ),
    "ticket_update": ("support_operations", "support ticket status escalation SOP"),
    "human_escalation": ("support_operations", "support escalation human review"),
}


class KnowledgeRetrievalStage:
    """Retrieve knowledge through a shared backend and create traceable evidence.

    Args:
        retriever: Provider-neutral lexical or Qdrant retrieval port.
    """

    def __init__(self, retriever: Retriever) -> None:
        """Initialize stage-two retrieval with the shared backend port."""
        self._retriever = retriever

    def run(
        self,
        request: GovernedRequest,
        classification: ClassificationResult,
    ) -> RetrievalResult:
        """Retrieve evidence using deterministic intent-specific query context.

        Args:
            request: Original governed request.
            classification: Stage-one intent used to select a policy route.

        Returns:
            Route, enriched query, retrieved chunks, and hashed evidence references.
        """
        route, enrichment = _ROUTES.get(
            classification.intent.value,
            ("general_support", "enterprise support policy FAQ"),
        )
        query = f"{request.query}\nPolicy context: {enrichment}"
        chunks = self._retriever.retrieve(query)
        evidence = [
            EvidenceReference(
                evidence_id=chunk.chunk_id,
                evidence_type=EvidenceType.KNOWLEDGE_CHUNK,
                source_id=chunk.document_id,
                title=chunk.title,
                content_sha256=chunk.content_sha256,
                score=chunk.score,
            )
            for chunk in chunks
        ]
        return RetrievalResult(
            route=route,
            query=query,
            chunks=chunks,
            evidence=evidence,
        )
