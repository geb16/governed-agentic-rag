"""Coordinate role-bound approvals with mandatory atomic audit events.

The service accepts caller decision data only after transport authentication supplies
a trusted principal. Actor identities are pseudonymized, and approval state never
commits without its corresponding audit record.
"""

from app.audit.schemas import AuditActorType, AuditEventType
from app.governance.contracts import (
    ApprovalCommand,
    ApprovalPrincipal,
    ApprovalStatus,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
)
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.errors import ApprovalAuthorizationError
from app.governance.orchestration.events import AuditRecorder
from app.governance.security import IdentityService


class ApprovalService:
    """Persist role-bound decisions and mandatory audit records atomically.

    Args:
        runtime: Injected workflow, audit, and transaction ports.
        events: Provider-neutral audit event recorder.
        identity: Service used to pseudonymize authenticated subjects.
    """

    def __init__(
        self,
        runtime: WorkflowRuntime,
        events: AuditRecorder,
        identity: IdentityService,
    ) -> None:
        """Initialize approval coordination from explicit ports and identity service."""
        self._runtime = runtime
        self._events = events
        self._identity = identity

    def pause(self, state: WorkflowState) -> WorkflowState:
        """Pause a workflow and audit each required role in one transaction.

        Args:
            state: Running workflow with a complete human-approval route.

        Returns:
            Persisted pending workflow containing role-specific approval records.
        """
        with self._runtime.unit_of_work.transaction():
            state = self._runtime.workflows.pause_for_approvals(
                state,
                expected_version=state.state_version,
            )
            for record in state.approvals:
                self._events.record(
                    state,
                    WorkflowStage.APPROVAL_ROUTING,
                    AuditEventType.APPROVAL_REQUESTED,
                    input_value={
                        "role": record.role,
                        "proposal_digest": record.proposal_digest,
                    },
                    details={"role": record.role, "approval_id": record.approval_id},
                )
            self._events.record(
                state,
                WorkflowStage.APPROVAL_ROUTING,
                AuditEventType.WORKFLOW_PAUSED,
                details={"reason": "human_approval_required"},
            )
        return state

    def decide(
        self,
        workflow_id: str,
        command: ApprovalCommand,
        principal: ApprovalPrincipal,
    ) -> WorkflowState:
        """Authorize and persist one proposal-bound approval decision.

        Args:
            workflow_id: Pending workflow identity.
            command: Role, decision, proposal digest, and expected state version.
            principal: Trusted authenticated subject and server-bound roles.

        Returns:
            Updated workflow, resumed only after all required roles approve.

        Raises:
            ApprovalAuthorizationError: If the principal lacks the requested role.
            ApprovalValidationError: If decision data is stale, expired, or mismatched.
            WorkflowConflictError: If workflow state changes concurrently.
        """
        if command.role not in principal.roles:
            raise ApprovalAuthorizationError(
                f"Authenticated principal is not authorized for role {command.role}"
            )
        actor_id = self._identity.pseudonym(principal.subject_id)
        with self._runtime.unit_of_work.transaction():
            state = self._runtime.workflows.decide_approval(
                workflow_id=workflow_id,
                role=command.role,
                approved=command.approved,
                actor_id=actor_id,
                proposal_digest=command.proposal_digest,
                expected_version=command.expected_state_version,
                comment=command.comment,
            )
            self._events.record(
                state,
                WorkflowStage.APPROVAL_ROUTING,
                AuditEventType.APPROVAL_RECORDED,
                actor=AuditActorType.HUMAN,
                actor_id=actor_id,
                input_value={
                    "role": command.role,
                    "proposal_digest": command.proposal_digest,
                    "expected_state_version": command.expected_state_version,
                },
                output_value={"approved": command.approved},
                details={"role": command.role, "approved": command.approved},
            )
            if not command.approved:
                state = self._runtime.workflows.update(
                    state.model_copy(
                        update={
                            "status": WorkflowStatus.DENIED,
                            "error_code": "approval_rejected",
                        }
                    ),
                    expected_version=state.state_version,
                )
            elif not self.has_pending(state) and self.all_approved(state):
                state = self._runtime.workflows.update(
                    state.model_copy(update={"status": WorkflowStatus.RUNNING}),
                    expected_version=state.state_version,
                )
                self.resumed(state)
        return state

    @staticmethod
    def has_pending(state: WorkflowState) -> bool:
        """Return whether any required approval remains undecided."""
        return any(item.status == ApprovalStatus.PENDING for item in state.approvals)

    @staticmethod
    def all_approved(state: WorkflowState) -> bool:
        """Return whether every required approval is explicitly approved."""
        return all(item.status == ApprovalStatus.APPROVED for item in state.approvals)

    def resumed(self, state: WorkflowState) -> None:
        """Record the transition from satisfied approvals into execution."""
        self._events.record(
            state,
            WorkflowStage.RETRY_RECOVERY,
            AuditEventType.WORKFLOW_RESUMED,
            details={"approved_roles": [item.role for item in state.approvals]},
        )
