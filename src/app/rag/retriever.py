from __future__ import annotations

import re
from collections import Counter
from typing import Protocol

from app.core.config import Settings
from app.domain.schemas import RetrievedChunk
from app.rag.chunking import KnowledgeChunk, load_knowledge_chunks
from app.rag.embeddings import OpenAIEmbeddingProvider
from app.rag.vector_store import QdrantVectorStore

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class Retriever(Protocol):
    @property
    def backend_name(self) -> str: ...

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]: ...


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class KnowledgeRetriever:
    """Trusted-corpus retriever with a production vector path and offline lexical path."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chunks = load_knowledge_chunks(
            settings.knowledge_base_dir,
            chunk_size=settings.chunk_size_chars,
            chunk_overlap=settings.chunk_overlap_chars,
        )
        self._doc_frequencies = self._build_document_frequencies(self._chunks)
        self._vector_store: QdrantVectorStore | None = None
        if settings.retrieval_backend == "qdrant":
            self._vector_store = QdrantVectorStore(
                settings,
                OpenAIEmbeddingProvider(settings),
            )
            if not self._vector_store.is_ready():
                raise RuntimeError("Qdrant collection is not ready; run scripts/ingest_kb.py first")

    @property
    def backend_name(self) -> str:
        return "qdrant" if self._vector_store is not None else "lexical"

    @staticmethod
    def _build_document_frequencies(chunks: list[KnowledgeChunk]) -> Counter[str]:
        frequencies: Counter[str] = Counter()
        for chunk in chunks:
            frequencies.update(set(_tokens(f"{chunk.title} {chunk.content}")))
        return frequencies

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        limit = min(top_k or self.settings.retrieval_top_k, 10)
        if self._vector_store is not None:
            return [
                result
                for result in self._vector_store.search(query, limit)
                if result.score >= self.settings.retrieval_min_score
            ]
        return (query, limit)
