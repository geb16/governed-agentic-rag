"""Declare provider-neutral structured model operations for governed stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from app.governance.contracts.execution import GovernedFinalDraft
from app.governance.contracts.state import WorkflowState
from app.governance.contracts.tasks import (
    ClassificationDraft,
    GovernedRequest,
    ProposedActionDraft,
    RetrievalResult,
)
from app.governance.contracts.tools import ToolDefinition

OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class ModelResult(Generic[OutputT]):
    """Pair one validated structured output with provider token accounting."""

    output: OutputT
    input_tokens: int = 0
    output_tokens: int = 0


class GovernanceModel(Protocol):
    """Provide only the three structured model operations required by governance."""

    @property
    def model_name(self) -> str:
        """Return the provider model identity recorded in workflow responses."""
        ...

    def classify(
        self,
        request: GovernedRequest,
        *,
        safety_identifier: str,
    ) -> ModelResult[ClassificationDraft]:
        """Classify a neutral request into a bounded structured draft."""
        ...

    def propose(
        self,
        request: GovernedRequest,
        classification: ClassificationDraft,
        retrieval: RetrievalResult,
        tools: list[ToolDefinition],
        *,
        safety_identifier: str,
    ) -> ModelResult[ProposedActionDraft]:
        """Propose one response or allowlisted action without executing it."""
        ...

    def finalize(
        self,
        state: WorkflowState,
        *,
        safety_identifier: str,
    ) -> ModelResult[GovernedFinalDraft]:
        """Draft a terminal response from persisted governed facts."""
        ...
