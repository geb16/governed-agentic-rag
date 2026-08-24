"""Translate workflow activity into stable provider-neutral audit events.

The recorder assigns workflow and trace identity consistently and supplies structured
values to the audit repository for digesting and keyed hash chaining. It does not own
storage or transaction boundaries.
"""

from __future__ import annotations

from typing import Any

from app.audit.ports import AuditRepository
from app.audit.schemas import AuditActorType, AuditEventType, AuditStage
from app.governance.contracts import STAGE_ORDER, WorkflowStage, WorkflowState


class AuditRecorder:
    """Translate workflow activity into provider-neutral append-only events.

    Args:
        repository: Audit port responsible for serialization and chain integrity.
    """

    def __init__(self, repository: AuditRepository) -> None:
        """Initialize the recorder with its append-only audit port."""
        self._repository = repository

    def workflow_started(self, state: WorkflowState) -> None:
        """Record initial request and case identities for a new workflow."""
        self._repository.append(
            workflow_id=state.workflow_id,
            trace_id=state.trace_id,
            stage=AuditStage.TASK_CLASSIFICATION,
            event_type=AuditEventType.WORKFLOW_STARTED,
            actor_type=AuditActorType.SYSTEM,
            input_value=state.request,
            details={
                "request_id": state.request.request_id,
                "case_id": state.request.case_id,
            },
        )

    def stage_started(self, state: WorkflowState, stage: WorkflowStage) -> None:
        """Record entry into a stage with its canonical one-based index."""
        self._repository.append(
            workflow_id=state.workflow_id,
            trace_id=state.trace_id,
            stage=AuditStage(stage.value),
            event_type=AuditEventType.STAGE_STARTED,
            actor_type=AuditActorType.SYSTEM,
            details={"stage_index": STAGE_ORDER.index(stage) + 1},
        )

    def stage_completed(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
        output: object,
        details: dict[str, object],
        *,
        actor: AuditActorType = AuditActorType.SYSTEM,
        event_type: AuditEventType = AuditEventType.STAGE_COMPLETED,
    ) -> None:
        """Record a stage output digest and bounded decision details.

        Args:
            state: Current workflow identity and trace context.
            stage: Completed governed stage.
            output: Structured value digested by the audit repository.
            details: Bounded searchable metadata safe for the audit record.
            actor: Trusted actor category responsible for the output.
            event_type: Completion or decision event identity.
        """
        self._repository.append(
            workflow_id=state.workflow_id,
            trace_id=state.trace_id,
            stage=AuditStage(stage.value),
            event_type=event_type,
            actor_type=actor,
            output_value=output,
            details=details,
        )

    def record(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
        event_type: AuditEventType,
        *,
        actor: AuditActorType = AuditActorType.SYSTEM,
        actor_id: str | None = None,
        input_value: Any | None = None,
        output_value: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append one explicitly typed audit event through the repository port."""
        self._repository.append(
            workflow_id=state.workflow_id,
            trace_id=state.trace_id,
            stage=AuditStage(stage.value),
            event_type=event_type,
            actor_type=actor,
            actor_id=actor_id,
            input_value=input_value,
            output_value=output_value,
            details=details,
        )

    def stage_skipped(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
        reason: str,
    ) -> None:
        """Record a deterministic reason why a stage was not entered."""
        self.record(
            state,
            stage,
            AuditEventType.STAGE_SKIPPED,
            details={"reason": reason},
        )

    def workflow_completed(self, state: WorkflowState) -> None:
        """Record terminal status and bounded error identity for the workflow."""
        self.record(
            state,
            WorkflowStage.FINAL_RESPONSE_AUDIT,
            AuditEventType.WORKFLOW_COMPLETED,
            output_value={
                "status": state.status.value,
                "error_code": state.error_code,
            },
            details={"status": state.status.value},
        )

    def stage_failed(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
        exc: Exception,
    ) -> None:
        """Record a bounded failure type without persisting exception text."""
        self.record(
            state,
            stage,
            AuditEventType.STAGE_FAILED,
            details={
                "error_type": type(exc).__name__,
                "error_code": "governance_stage_failed",
            },
        )
