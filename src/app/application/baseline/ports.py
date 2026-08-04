from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.domain.schemas import (
    AgentDraft,
    BaselineRequest,
    BaselineResponse,
    ModelTurn,
    RetrievedChunk,
    ToolCallRecord,
    ToolExecutionContext,
)


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    """Provider-neutral result returned by an input or output safety policy."""

    blocked: bool
    category: str | None = None
    normalized_text: str = ""


@dataclass(slots=True)
class ToolExecution:
    """Result envelope returned by the controlled-tool port."""

    output_json: str
    record: ToolCallRecord
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)


class CaseReader(Protocol):
    def case_exists(self, case_id: str) -> bool: ...


class RetrievalGateway(Protocol):
    @property
    def backend_name(self) -> str: ...

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]: ...


class ModelGateway(Protocol):
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


class ToolGateway(Protocol):
    @property
    def specs(self) -> list[dict[str, Any]]: ...

    def execute(
        self,
        *,
        call_id: str,
        name: str,
        arguments_json: str,
        context: ToolExecutionContext,
    ) -> ToolExecution: ...


class InputSafetyPolicy(Protocol):
    def inspect(self, text: str, *, max_chars: int) -> SafetyDecision: ...


class OutputSafetyPolicy(Protocol):
    def inspect(
        self,
        draft: AgentDraft,
        *,
        allowed_chunk_ids: set[str],
    ) -> SafetyDecision: ...


class BaselineUseCase(Protocol):
    """Stable API-facing boundary for the baseline invocation use case."""

    def invoke(self, request: BaselineRequest) -> BaselineResponse: ...
