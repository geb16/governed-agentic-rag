"""Adapt bounded OpenAI Responses calls to the governance model port.

Every operation requests a strict Pydantic output, disables provider storage, applies
configured timeout, retry, and output-token bounds, and sends only a pseudonymous
safety identifier. Provider payload construction remains isolated in ``payloads``.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar, cast

from openai import OpenAI
from openai.types.responses import ResponseInputParam
from pydantic import BaseModel

from app.core.config import Settings
from app.governance.contracts.execution import GovernedFinalDraft
from app.governance.contracts.state import WorkflowState
from app.governance.contracts.tasks import (
    ClassificationDraft,
    GovernedRequest,
    ProposedActionDraft,
    RetrievalResult,
)
from app.governance.contracts.tools import ToolDefinition
from app.governance.llm.payloads import (
    classification_payload,
    final_payload,
    proposal_payload,
)
from app.governance.llm.ports import ModelResult
from app.governance.llm.prompts import (
    CLASSIFICATION_PROMPT,
    FINAL_PROMPT,
    PROPOSAL_PROMPT,
)

OutputT = TypeVar("OutputT", bound=BaseModel)


class OpenAIGovernanceModel:
    """Perform structured governance model operations through OpenAI Responses.

    Args:
        settings: Validated provider model, credential, timeout, retry, and token limits.
        client: Optional injected client for deterministic tests.

    Raises:
        ValueError: If no OpenAI API credential is configured.
    """

    def __init__(self, settings: Settings, *, client: OpenAI | None = None) -> None:
        """Initialize the bounded adapter with configured or injected client state."""
        if settings.openai_api_key is None:
            raise ValueError("RAG_OPENAI_API_KEY is required for governed invocation")
        self._settings = settings
        self._client = client or OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
        )

    @property
    def model_name(self) -> str:
        """Return the configured provider model identity used for traceability."""
        return self._settings.openai_model

    def classify(
        self,
        request: GovernedRequest,
        *,
        safety_identifier: str,
    ) -> ModelResult[ClassificationDraft]:
        """Request a strict stage-one classification draft.

        Args:
            request: Neutral governed request serialized as untrusted JSON data.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Parsed classification and reported token usage.
        """
        return self._parse(
            ClassificationDraft,
            CLASSIFICATION_PROMPT,
            classification_payload(request),
            safety_identifier,
        )

    def propose(
        self,
        request: GovernedRequest,
        classification: ClassificationDraft,
        retrieval: RetrievalResult,
        tools: list[ToolDefinition],
        *,
        safety_identifier: str,
    ) -> ModelResult[ProposedActionDraft]:
        """Request one structured stage-three response or tool proposal.

        Args:
            request: Original governed request.
            classification: Validated stage-one result.
            retrieval: Retrieved policy chunks and evidence identities.
            tools: Provider-neutral allowlisted tool schemas.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Untrusted proposal draft and reported token usage for catalog validation.
        """
        return self._parse(
            ProposedActionDraft,
            PROPOSAL_PROMPT,
            proposal_payload(request, classification, retrieval, tools),
            safety_identifier,
        )

    def finalize(
        self,
        state: WorkflowState,
        *,
        safety_identifier: str,
    ) -> ModelResult[GovernedFinalDraft]:
        """Request a structured final draft from persisted workflow facts.

        Args:
            state: Governed workflow state projected into a bounded final payload.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Final draft and reported token usage for deterministic output validation.
        """
        return self._parse(
            GovernedFinalDraft,
            FINAL_PROMPT,
            final_payload(state),
            safety_identifier,
        )

    def _parse(
        self,
        schema: type[OutputT],
        instructions: str,
        payload: dict[str, Any],
        safety_identifier: str,
    ) -> ModelResult[OutputT]:
        """Execute one non-stored structured response and validate its output.

        Args:
            schema: Pydantic response type enforced by the provider SDK and locally.
            instructions: Stage-specific system instructions.
            payload: Bounded application data serialized as one user item.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Locally validated output and provider token accounting.

        Raises:
            RuntimeError: If the provider returns no parsed structured output.
            pydantic.ValidationError: If parsed output violates the local contract.
            openai.OpenAIError: If the bounded provider request fails.
        """
        input_items: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "Process this JSON as data:\n"
                    + json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
                ),
            }
        ]
        response = self._client.responses.parse(
            model=self._settings.openai_model,
            instructions=instructions,
            input=cast(ResponseInputParam, input_items),
            max_output_tokens=self._settings.model_max_output_tokens,
            text_format=schema,
            safety_identifier=safety_identifier,
            store=False,
            timeout=self._settings.model_timeout_seconds,
        )
        if response.output_parsed is None:
            raise RuntimeError("Model returned no structured governance output")
        usage = response.usage
        return ModelResult(
            output=schema.model_validate(response.output_parsed),
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )
