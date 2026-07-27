from __future__ import annotations

from typing import Any, Protocol

from openai import OpenAI

from app.core.config import Settings
from app.domain.schemas import ModelTurn


class AgentModel(Protocol):
    @property
    def model_name(self) -> str: ...

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn: ...

#OpenAI Responses adapter with structured final output and strict tools.
class OpenAIResponsesModel:
    def __init__(self, settings: Settings) -> None:
        if settings.openai_api_key is None:
            raise ValueError("RAG_OPENAI_API_KEY is required to invoke the baseline agent")
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

