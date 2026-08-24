"""Implement stage three: candidate response or action generation.

The model sees provider-neutral metadata for allowlisted capabilities. Its proposal
remains untrusted until the deterministic catalog validates the tool name, JSON
arguments, and exact parameter schema.
"""

from __future__ import annotations

from app.governance.contracts import (
    ClassificationResult,
    GovernedRequest,
    ProposedAction,
    RetrievalResult,
)
from app.governance.llm import GovernanceModel, ModelResult
from app.governance.tools.catalog import ToolCatalog


class ProposedActionStage:
    """Generate a structured proposal and apply deterministic allowlist validation.

    Args:
        model: Provider-neutral model port used to draft the candidate action.
        tool_catalog: Validate-only view of shared simulated capabilities.
    """

    def __init__(self, model: GovernanceModel, tool_catalog: ToolCatalog) -> None:
        """Initialize proposal generation and validate-only tool metadata."""
        self._model = model
        self._tool_catalog = tool_catalog

    def run(
        self,
        request: GovernedRequest,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
        *,
        safety_identifier: str,
    ) -> ModelResult[ProposedAction]:
        """Return a proposal enriched with trusted tool-validation results.

        Args:
            request: Original neutral governed request.
            classification: Validated stage-one classification.
            retrieval: Stage-two evidence and route.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Validated proposal plus provider token usage.
        """
        result = self._model.propose(
            request,
            classification,
            retrieval,
            self._tool_catalog.definitions,
            safety_identifier=safety_identifier,
        )
        return ModelResult(
            output=self._tool_catalog.validate(result.output),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
