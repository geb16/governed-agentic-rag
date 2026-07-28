from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.core.config import Settings
from app.rag.chunking import KnowledgeChunk
from app.rag.embeddings import EmbeddingProvider


class QdrantVectorStore:
    """Minimal Qdrant adapter. The baseline owns retrieval, not workflow state."""

    def __init__(
        self,
        settings: Settings,
        embeddings: EmbeddingProvider,
        *,
        write_access: bool = False,
    ) -> None:
        if settings.qdrant_url is None:
            raise ValueError("Qdrant URL is required")
        configured_key = (
            settings.qdrant_admin_api_key if write_access else settings.qdrant_read_api_key
        )
        api_key = configured_key.get_secret_value() if configured_key is not None else None
        if api_key and not settings.qdrant_url.lower().startswith("https://"):
            raise ValueError("Qdrant API keys may only be sent over HTTPS")
        self._client = QdrantClient(
            url=settings.qdrant_url,
            api_key=api_key,
            timeout=settings.qdrant_timeout_seconds,
            check_compatibility=True,
        )
        self._collection = settings.qdrant_collection
        self._embeddings = embeddings

    def replace(self, chunks: list[KnowledgeChunk]) -> int:
        vectors = self._embeddings.embed([f"{chunk.title}\n\n{chunk.content}" for chunk in chunks])
        if len(vectors) != len(chunks) or not vectors:
            raise RuntimeError("Embedding provider returned an invalid vector count")
        dimension = len(vectors[0])
        if dimension == 0 or any(len(vector) != dimension for vector in vectors):
            raise RuntimeError("Embedding provider returned inconsistent dimensions")

        if self._client.collection_exists(self._collection):
            self._client.delete_collection(self._collection)
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
        )
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, chunk.chunk_id)),
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "content": chunk.content,
                    "source_path": chunk.source_path,
                    "content_sha256": chunk.content_sha256,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points, wait=True)
        return len(points)
