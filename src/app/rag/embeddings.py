"""Embedding port and OpenAI adapter used by vector retrieval."""

from __future__ import annotations

from typing import Protocol

from openai import OpenAI

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    """Boundary for converting ordered text inputs into ordered vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input string."""
        ...


class OpenAIEmbeddingProvider:
    """OpenAI embeddings implementation configured with bounded retries and timeout."""

    def __init__(self, settings: Settings) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OpenAI API key is required for vector retrieval")
        self._model = settings.openai_embedding_model
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed text in input order, returning an empty list for empty input."""
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
