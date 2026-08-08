from __future__ import annotations

from typing import Protocol

from openai import OpenAI

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider:
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
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
