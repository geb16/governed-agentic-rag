"""Trusted-corpus retrieval port with lexical and Qdrant implementations."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol

from app.core.config import Settings
from app.domain.evidence import RetrievedChunk
from app.rag.chunking import KnowledgeChunk, load_knowledge_chunks
from app.rag.embeddings import OpenAIEmbeddingProvider
from app.rag.vector_store import QdrantVectorStore

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class Retriever(Protocol):
    """Boundary shared by knowledge consumers and the policy lookup tool."""

    @property
    def backend_name(self) -> str:
        """Return the active backend identifier."""
        ...

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return ranked approved chunks for a query."""
        ...


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
        """Return ``qdrant`` or ``lexical`` for reproducibility metadata."""
        return "qdrant" if self._vector_store is not None else "lexical"

    @staticmethod
    def _build_document_frequencies(chunks: list[KnowledgeChunk]) -> Counter[str]:
        frequencies: Counter[str] = Counter()
        for chunk in chunks:
            frequencies.update(set(_tokens(f"{chunk.title} {chunk.content}")))
        return frequencies

    def _lexical_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        query_terms = Counter(_tokens(query))
        if not query_terms:
            return []
        total_chunks = len(self._chunks)
        scored: list[tuple[float, KnowledgeChunk]] = []
        for chunk in self._chunks:
            document_terms = Counter(_tokens(f"{chunk.title} {chunk.content}"))
            raw_score = 0.0
            for term, query_frequency in query_terms.items():
                term_frequency = document_terms[term]
                if term_frequency == 0:
                    continue
                inverse_frequency = math.log(
                    1 + (total_chunks + 1) / (self._doc_frequencies[term] + 1)
                )
                raw_score += query_frequency * (1 + math.log(term_frequency)) * inverse_frequency
            if raw_score > 0:
                normalized = raw_score / (raw_score + 4.0)
                scored.append((min(1.0, normalized), chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.title,
                content=chunk.content,
                source_path=chunk.source_path,
                score=round(score, 6),
                content_sha256=chunk.content_sha256,
            )
            for score, chunk in scored[:top_k]
            if score >= self.settings.retrieval_min_score
        ]

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Retrieve up to ten chunks above the configured minimum score."""
        limit = min(top_k or self.settings.retrieval_top_k, 10)
        if self._vector_store is not None:
            return [
                result
                for result in self._vector_store.search(query, limit)
                if result.score >= self.settings.retrieval_min_score
            ]
        return self._lexical_search(query, limit)

    @property
    def chunk_count(self) -> int:
        """Return the number of integrity-validated local chunks."""
        return len(self._chunks)
