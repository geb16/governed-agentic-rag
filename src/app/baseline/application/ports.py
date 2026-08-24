"""Inbound and outbound ports used by the baseline application layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.baseline.application.contracts import (
    BaselineRequest,
    BaselineResponse,
    ToolCallRecord,
)
from app.domain.evidence import RetrievedChunk
from app.domain.model import (
    AgentDraft,
    ModelTurn,
)
from app.domain.tasks import ToolExecutionContext


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
    """Read-only boundary for validating isolated evaluation cases."""

    def case_exists(self, case_id: str) -> bool:
        """Return whether a synthetic case exists."""
        ...


class RetrievalGateway(Protocol):
    """Boundary for retrieving approved knowledge chunks."""

    @property
    def backend_name(self) -> str:
        """Return the stable retrieval-backend identifier."""
        ...

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return ranked chunks for a normalized query."""
        ...


class ModelGateway(Protocol):
    """Provider-neutral boundary for one structured model turn."""

    @property
    def model_name(self) -> str:
        """Return the configured model identifier."""
        ...

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        """Generate one bounded turn from provider conversation items."""
        ...


class ToolGateway(Protocol):
    """Boundary for allowlisted tool schemas and controlled execution."""

    @property
    def specs(self) -> list[dict[str, Any]]:
        """Return strict function definitions exposed to the model."""
        ...

    def execute(
        self,
        *,
        call_id: str,
        name: str,
        arguments_json: str,
        context: ToolExecutionContext,
    ) -> ToolExecution:
        """Validate and execute one model-proposed tool call."""
        ...


class InputSafetyPolicy(Protocol):
    """Boundary for deterministic input normalization and screening."""

    def inspect(self, text: str, *, max_chars: int) -> SafetyDecision:
        """Inspect user text against bounded input rules."""
        ...


class OutputSafetyPolicy(Protocol):
    """Boundary for deterministic final-output validation."""

    def inspect(
        self,
        draft: AgentDraft,
        *,
        allowed_chunk_ids: set[str],
    ) -> SafetyDecision:
        """Inspect a structured draft against evidence and content rules."""
        ...


class BaselineUseCase(Protocol):
    """Stable API-facing boundary for the baseline invocation use case."""

    def invoke(self, request: BaselineRequest) -> BaselineResponse:
        """Execute one isolated baseline task and return its public outcome."""
        ...
