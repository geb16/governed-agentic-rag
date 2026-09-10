"""Records when a model request crosses the safe-retry boundary.

References:
    [1] OpenAI, "Error handling," OpenAI Python SDK.
        https://github.com/openai/openai-python#handling-errors
"""

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
    """Applies the experiment's acceptance policy to a model exception.

    Connection, timeout, and API status errors remain pre-acceptance under the
    protocol. Other errors conservatively mark the request accepted to prevent
    an unsafe retry after a response may have been received or processed.
    """
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
        """Returns the wrapped model's identifier."""
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
        """Delegates completion and records its acceptance boundary."""
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
        """Returns the wrapped model's identifier."""
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
        """Delegates classification and records its acceptance boundary."""
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
        """Delegates action proposal and records its acceptance boundary."""
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
        """Delegates finalization and records its acceptance boundary."""
        try:
            result = self._delegate.finalize(state, safety_identifier=safety_identifier)
        except Exception as error:
            self._last_error = error
            _record_error_boundary(error, self._recorder)
            raise
        self._recorder.mark_accepted()
        return result
