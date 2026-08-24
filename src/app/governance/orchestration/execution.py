"""Coordinate stage-six execution, recovery, persistence, and audit events."""

from app.audit.schemas import AuditActorType, AuditEventType
from app.baseline.application.contracts import ToolCallRecord, ToolStatus
from app.domain.tasks import ToolExecutionContext
from app.governance.contracts import (
    RecoveryDisposition,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
)
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.events import AuditRecorder
from app.governance.orchestration.state import WorkflowStateService


class ExecutionRunner:
    """Execute bounded recovery and atomically checkpoint attempts and outcome.

    Args:
        runtime: Injected recovery, persistence, audit, and transaction ports.
        states: Workflow state checkpoint service.
        events: Stable audit event recorder.
    """

    def __init__(
        self,
        runtime: WorkflowRuntime,
        states: WorkflowStateService,
        events: AuditRecorder,
    ) -> None:
        """Initialize stage-six coordination from explicit runtime services."""
        self._runtime = runtime
        self._states = states
        self._events = events

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute stage six and persist all attempts with its recovery result.

        Args:
            state: Approved or automatically routed workflow with a proposal.

        Returns:
            Running state after success or failed state after safe termination.

        Raises:
            RuntimeError: If orchestration reaches execution without a proposal.
        """
        stage = WorkflowStage.RETRY_RECOVERY
        if state.proposal is None:
            raise RuntimeError("Proposal is required before execution")
        self._events.stage_started(state, stage)
        result, records = self._runtime.recovery.run(
            state.proposal,
            ToolExecutionContext(
                case_id=state.request.case_id,
                request_id=state.request.request_id,
                requester_id=state.request.requester_id,
            ),
        )
        failed = result.disposition == RecoveryDisposition.SAFE_TERMINATION
        candidate = state.model_copy(
            update={
                "recovery": result,
                "tool_calls": [*state.tool_calls, *records],
                "status": WorkflowStatus.FAILED if failed else WorkflowStatus.RUNNING,
                "error_code": result.error_code if failed else None,
            }
        )
        with self._runtime.unit_of_work.transaction():
            self._record_attempts(state, records)
            state = self._states.save_stage(candidate, stage)
            self._events.stage_completed(
                state,
                stage,
                result,
                {
                    "disposition": result.disposition.value,
                    "attempts": result.attempts,
                    "error_code": result.error_code,
                },
            )
        return state

    def _record_attempts(
        self,
        state: WorkflowState,
        records: list[ToolCallRecord],
    ) -> None:
        """Record each tool outcome and any deterministic retry scheduling."""
        for attempt, record in enumerate(records, start=1):
            self._events.record(
                state,
                WorkflowStage.RETRY_RECOVERY,
                AuditEventType.TOOL_ATTEMPTED,
                actor=AuditActorType.TOOL,
                input_value=record.proposal,
                output_value=record.outcome,
                details={
                    "attempt": attempt,
                    "tool_name": record.tool_name,
                    "status": record.status.value,
                    "error_code": record.outcome.error_code,
                    "retryable": record.outcome.retryable,
                },
            )
            if (
                record.status == ToolStatus.FAILED
                and record.outcome.retryable
                and attempt < self._runtime.recovery.max_attempts
            ):
                self._events.record(
                    state,
                    WorkflowStage.RETRY_RECOVERY,
                    AuditEventType.RETRY_SCHEDULED,
                    details={
                        "completed_attempt": attempt,
                        "next_attempt": attempt + 1,
                    },
                )
