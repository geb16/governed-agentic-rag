"""Coordinate stage-seven output validation and fail-closed termination."""

from app.audit.schemas import AuditActorType
from app.governance.contracts import (
    GovernedFinalDraft,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
)
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.events import AuditRecorder
from app.governance.orchestration.state import WorkflowStateService
from app.governance.security import IdentityService
from app.governance.stages.final_response import UnsafeGovernedOutputError


class FinalizationRunner:
    """Guard, persist, and audit a terminal response or safe failure.

    Args:
        runtime: Injected final stage, persistence, audit, and transaction ports.
        states: Workflow state checkpoint service.
        events: Stable audit event recorder.
        identity: Service producing pseudonymous provider safety identities.
    """

    def __init__(
        self,
        runtime: WorkflowRuntime,
        states: WorkflowStateService,
        events: AuditRecorder,
        identity: IdentityService,
    ) -> None:
        """Initialize terminal coordination and pseudonymous model identity."""
        self._runtime = runtime
        self._states = states
        self._events = events
        self._identity = identity

    def run(self, state: WorkflowState) -> WorkflowState:
        """Produce, validate, checkpoint, and audit the final response.

        Model or guardrail failures become a bounded ungrounded failure response.
        State, stage completion, and workflow completion commit atomically.

        Args:
            state: Workflow containing all planning, approval, and execution facts.

        Returns:
            Terminal completed, denied, clarification, or failed workflow state.
        """
        stage = WorkflowStage.FINAL_RESPONSE_AUDIT
        self._events.stage_started(state, stage)
        try:
            result = self._runtime.final.run(
                state,
                safety_identifier=self._identity.pseudonym(state.request.requester_id),
            )
            status = (
                WorkflowStatus.COMPLETED if state.status == WorkflowStatus.RUNNING else state.status
            )
            candidate = state.model_copy(
                update={
                    "final": result.output,
                    "status": status,
                    "usage": self._states.add_usage(
                        state.usage,
                        result.input_tokens,
                        result.output_tokens,
                    ),
                }
            )
        except Exception as exc:
            error_code = (
                exc.category
                if isinstance(exc, UnsafeGovernedOutputError)
                else "final_response_generation_failed"
            )
            candidate = state.model_copy(
                update={
                    "final": GovernedFinalDraft(
                        answer="The governed workflow could not safely produce a response.",
                        grounded=False,
                    ),
                    "status": WorkflowStatus.FAILED,
                    "error_code": error_code,
                }
            )
        with self._runtime.unit_of_work.transaction():
            state = self._states.save_stage(candidate, stage)
            self._events.stage_completed(
                state,
                stage,
                state.final,
                {
                    "status": state.status.value,
                    "grounded": state.final.grounded if state.final else False,
                    "error_code": state.error_code,
                },
                actor=AuditActorType.MODEL,
            )
            self._events.workflow_completed(state)
        return state

    def fail_closed(
        self,
        state: WorkflowState,
        exc: Exception,
        *,
        stage: WorkflowStage,
    ) -> WorkflowState:
        """Persist a safe terminal response after an unexpected stage failure.

        Args:
            state: Last durable workflow state.
            exc: Internal failure used only for bounded audit classification.
            stage: Stage responsible for the failure.

        Returns:
            Failed workflow containing a stable public response and error code.
        """
        candidate = state.model_copy(
            update={
                "status": WorkflowStatus.FAILED,
                "error_code": "governance_stage_failed",
                "final": GovernedFinalDraft(
                    answer="The governed workflow could not safely complete the request.",
                    grounded=False,
                ),
            }
        )
        with self._runtime.unit_of_work.transaction():
            state = self._runtime.workflows.update(
                candidate,
                expected_version=state.state_version,
            )
            self._events.stage_failed(state, stage, exc)
        return state
