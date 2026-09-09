"""Model decorators that persist the first successful provider response."""

from __future__ import annotations

from typing import Any

from app.baseline.application.ports import ModelGateway
from app.domain.model import ModelTurn
from app.governance.contracts import (
    ClassificationDraft,
    GovernedFinalDraft,
    GovernedRequest,
    ProposedActionDraft,
    RetrievalResult,
    ToolDefinition,
    WorkflowState,
)
from app.governance.llm import GovernanceModel, ModelResult
from openai import APIConnectionError, APIStatusError

from paired_agent_evaluation.application.ports import AcceptanceRecorder

PRE_ACCEPTANCE_ERRORS = (APIConnectionError, APIStatusError, ConnectionError, TimeoutError)


def _record_error_boundary(error: Exception, recorder: AcceptanceRecorder) -> None:
    """Treat only provider rejection or transport failure as pre-acceptance."""
    if not isinstance(error, PRE_ACCEPTANCE_ERRORS):
        recorder.mark_accepted()


class AcceptanceAwareBaselineModel:
    """Record acceptance after the baseline provider returns its first model turn."""

    def __init__(self, delegate: ModelGateway, recorder: AcceptanceRecorder) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._last_error: Exception | None = None

    @property
    def model_name(self) -> str:
        return self._delegate.model_name

    @property
    def last_error(self) -> Exception | None:
        """Return the latest provider error when no response established acceptance."""
        return self._last_error

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        try:
            result = self._delegate.complete(
                input_items=input_items,
                instructions=instructions,
                tools=tools,
                safety_identifier=safety_identifier,
            )
        except Exception as error:
            self._last_error = error
            _record_error_boundary(error, self._recorder)
            raise
        self._recorder.mark_accepted()
        return result


class AcceptanceAwareGovernanceModel:
    """Record acceptance after the governed provider returns its first stage result."""

    def __init__(self, delegate: GovernanceModel, recorder: AcceptanceRecorder) -> None:
        self._delegate = delegate
        self._recorder = recorder
        self._last_error: Exception | None = None

    @property
    def model_name(self) -> str:
        return self._delegate.model_name

    @property
    def last_error(self) -> Exception | None:
        """Return the latest provider error when no response established acceptance."""
        return self._last_error

    def classify(
        self,
        request: GovernedRequest,
        *,
        safety_identifier: str,
    ) -> ModelResult[ClassificationDraft]:
        try:
            result = self._delegate.classify(request, safety_identifier=safety_identifier)
        except Exception as error:
            self._last_error = error
            _record_error_boundary(error, self._recorder)
            raise
        self._recorder.mark_accepted()
        return result

    def propose(
        self,
        request: GovernedRequest,
        classification: ClassificationDraft,
        retrieval: RetrievalResult,
        tools: list[ToolDefinition],
        *,
        safety_identifier: str,
    ) -> ModelResult[ProposedActionDraft]:
        try:
            result = self._delegate.propose(
                request,
                classification,
                retrieval,
                tools,
                safety_identifier=safety_identifier,
            )
        except Exception as error:
            self._last_error = error
            _record_error_boundary(error, self._recorder)
            raise
        self._recorder.mark_accepted()
        return result

    def finalize(
        self,
        state: WorkflowState,
        *,
        safety_identifier: str,
    ) -> ModelResult[GovernedFinalDraft]:
        try:
            result = self._delegate.finalize(state, safety_identifier=safety_identifier)
        except Exception as error:
            self._last_error = error
            _record_error_boundary(error, self._recorder)
            raise
        self._recorder.mark_accepted()
        return result
