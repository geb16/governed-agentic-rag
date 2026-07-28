from __future__ import annotations

from qdrant_client import QdrantClient

from app.core.config import Settings
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