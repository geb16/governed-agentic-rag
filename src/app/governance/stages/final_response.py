"""Implement stage seven: grounded final-response validation.

The model drafts an answer, but the shared deterministic output guardrail decides
whether the draft may leave the application. Citations are restricted to evidence
retrieved or produced by simulated tools in the active workflow.
"""

from __future__ import annotations

from app.baseline.application.guardrails import OutputGuardrail
from app.domain.model import AgentDraft
from app.governance.contracts import GovernedFinalDraft, WorkflowState
from app.governance.llm import GovernanceModel, ModelResult


class UnsafeGovernedOutputError(RuntimeError):
    """Signal that deterministic output validation rejected the final draft.

    Attributes:
        category: Stable guardrail category suitable for bounded audit and recovery.
    """

    def __init__(self, category: str | None) -> None:
        """Initialize the error with a stable guardrail category."""
        super().__init__(category or "unsafe_governed_output")
        self.category = category or "unsafe_governed_output"


class FinalResponseStage:
    """Draft and validate the terminal grounded response.

    Args:
        model: Provider-neutral model port used only to create the draft.
    """

    def __init__(self, model: GovernanceModel) -> None:
        """Initialize final drafting with the model port and shared guardrail."""
        self._model = model
        self._guardrail = OutputGuardrail()

    def run(
        self,
        state: WorkflowState,
        *,
        safety_identifier: str,
    ) -> ModelResult[GovernedFinalDraft]:
        """Generate a final draft and fail closed on unsafe or unknown citations.

        Args:
            state: Current workflow containing all eligible evidence identities.
            safety_identifier: Pseudonymous provider safety identity.

        Returns:
            Validated final draft and provider token usage.

        Raises:
            UnsafeGovernedOutputError: If safety, grounding, or citation checks fail.
        """
        result = self._model.finalize(state, safety_identifier=safety_identifier)
        allowed_ids = {
            item.evidence_id for item in (state.retrieval.evidence if state.retrieval else [])
        }
        for call in state.tool_calls:
            allowed_ids.update(item.evidence_id for item in call.evidence)
        decision = self._guardrail.inspect(
            AgentDraft(
                answer=result.output.answer,
                cited_chunk_ids=result.output.cited_evidence_ids,
                grounded=result.output.grounded,
            ),
            allowed_chunk_ids=allowed_ids,
        )
        if decision.blocked:
            raise UnsafeGovernedOutputError(decision.category)
        return result
