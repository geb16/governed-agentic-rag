from __future__ import annotations

from app.domain.evidence import RetrievedChunk


class StaticRetriever:
    backend_name = "qdrant"

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="policy:test:0",
                document_id="support_policy",
                title="Support policy",
                content="Support agents may answer approved policy questions.",
                source_path="synthetic.md",
                score=1.0,
                content_sha256="a" * 64,
            )
        ]
