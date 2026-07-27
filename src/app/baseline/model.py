from __future__ import annotations

from typing import Any, Protocol

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
