"""Administrative ingestion use case for the approved Qdrant collection."""

from __future__ import annotations

from app.core.config import Settings
from app.rag.chunking import load_knowledge_chunks
from app.rag.embeddings import OpenAIEmbeddingProvider
from app.rag.vector_store import QdrantVectorStore


def ingest(settings: Settings) -> int:
    """Replace the configured Qdrant collection with validated knowledge chunks.

    Args:
        settings: Validated settings containing write credentials and chunk parameters.

    Returns:
        Number of vector points written.

    Raises:
        ValueError: If the configured backend is not Qdrant or inputs are invalid.
        RuntimeError: If embedding output is inconsistent.
    """
    if settings.retrieval_backend != "qdrant":
        raise ValueError("Set RAG_RETRIEVAL_BACKEND=qdrant before vector ingestion")
    chunks = load_knowledge_chunks(
        settings.knowledge_base_dir,
        chunk_size=settings.chunk_size_chars,
        chunk_overlap=settings.chunk_overlap_chars,
    )
    store = QdrantVectorStore(
        settings,
        OpenAIEmbeddingProvider(settings),
        write_access=True,
    )
    return store.replace(chunks)
