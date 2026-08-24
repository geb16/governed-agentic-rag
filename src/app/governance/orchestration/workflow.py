"""Implement the public seven-stage governed workflow use case.

The use case owns idempotent invocation, deterministic input screening, planning,
approval pause and resume, bounded execution, finalization, and fail-closed recovery.
All required state and audit mutations share explicit transaction boundaries.
"""

from app.audit.schemas import AuditTrace
from app.baseline.application.guardrails import InputGuardrail
from app.governance.contracts import (
    ApprovalCommand,
    ApprovalDecision,
    ApprovalPrincipal,
    GovernedRequest,
    GovernedResponse,
    WorkflowConflictError,
    WorkflowStage,
    WorkflowStatus,
    WorkflowSummary,
)
from app.governance.orchestration.approvals import ApprovalService
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.errors import StageExecutionError
from app.governance.orchestration.events import AuditRecorder
from app.governance.orchestration.execution import ExecutionRunner
from app.governance.orchestration.finalization import FinalizationRunner
from app.governance.orchestration.planning import PlanningRunner
from app.governance.orchestration.state import WorkflowStateService
from app.governance.security import IdentityService


class GovernedWorkflow:
    """Expose the explicit seven-stage governed state machine.

    Args:
        runtime: Fully composed provider-neutral ports and bounded stage services.
    """

    def __init__(self, runtime: WorkflowRuntime) -> None:
        """Initialize the use case and its focused orchestration services."""
        self._runtime = runtime
        self._states = WorkflowStateService(runtime)
        self._events = AuditRecorder(runtime.audit)
        identity = IdentityService(runtime.settings)
        self._planning = PlanningRunner(runtime, self._states, self._events, identity)
        self._approvals = ApprovalService(runtime, self._events, identity)
        self._execution = ExecutionRunner(runtime, self._states, self._events)
        self._finalization = FinalizationRunner(
            runtime,
            self._states,
            self._events,
            identity,
        )
        self._input_guardrail = InputGuardrail()

    def invoke(self, request: GovernedRequest) -> GovernedResponse:
        """Create, run, pause, or idempotently replay a governed invocation.

        The same request ID and identical immutable input returns prior state without
        additional model, retrieval, tool, or audit work. Reuse with different input
        fails as a conflict.

        Args:
            request: Strict neutral task input shared with the baseline condition.

        Returns:
            Completed, pending, denied, clarification-required, or safely failed state.

        Raises:
            WorkflowConflictError: If a request ID is rebound to different input.
            UnknownSyntheticCaseError: If the requested synthetic case is absent.
        """
        with self._runtime.unit_of_work.transaction():
            existing = self._states.find_by_request_id(request.request_id)
            if existing is not None:
                if existing.request != request:
                    raise WorkflowConflictError(
                        f"Request ID {request.request_id} is already bound to different input"
                    )
                return self._states.response(existing)
            state = self._states.create(request)
            self._events.workflow_started(state)
        active_stage = WorkflowStage.TASK_CLASSIFICATION
        try:
            decision = self._input_guardrail.inspect(
                request.query,
                max_chars=self._runtime.settings.max_query_chars,
            )
            state = self._planning.run(
                state,
                security_category=decision.category if decision.blocked else None,
            )
            route = state.approval_route
            if route is None:
                raise RuntimeError("Approval routing did not produce a route")
            if route.decision == ApprovalDecision.REQUIRE_HUMAN:
                active_stage = WorkflowStage.APPROVAL_ROUTING
                state = self._approvals.pause(state)
                return self._states.response(state)
            if route.decision == ApprovalDecision.DENY:
                state = self._states.set_status(
                    state,
                    WorkflowStatus.DENIED,
                    error_code="governance_denied",
                )
            elif route.decision == ApprovalDecision.REQUEST_CLARIFICATION:
                state = self._states.set_status(
                    state,
                    WorkflowStatus.CLARIFICATION_REQUIRED,
                    error_code="clarification_required",
                )
            else:
                active_stage = WorkflowStage.RETRY_RECOVERY
                state = self._execution.run(state)
            active_stage = WorkflowStage.FINAL_RESPONSE_AUDIT
            state = self._finalization.run(state)
        except Exception as exc:
            if isinstance(exc, StageExecutionError):
                state = exc.state
                failure = exc.cause
                failed_stage = exc.stage
            else:
                failure = exc
                failed_stage = active_stage
            state = self._finalization.fail_closed(state, failure, stage=failed_stage)
        return self._states.response(state)

    def approve(
        self,
        workflow_id: str,
        command: ApprovalCommand,
        principal: ApprovalPrincipal,
    ) -> GovernedResponse:
        """Apply one approval and resume only after every required role approves.

        Args:
            workflow_id: Pending workflow identity.
            command: Proposal-bound decision and expected state version.
            principal: Trusted authenticated subject and server-side roles.

        Returns:
            Pending state, denied terminal state, or executed and finalized state.

        Raises:
            UnknownWorkflowError: If the workflow does not exist.
            ApprovalAuthorizationError: If the principal lacks the decision role.
            ApprovalValidationError: If the decision is stale, expired, or mismatched.
            WorkflowConflictError: If the workflow changes concurrently.
        """
        self._states.require(workflow_id)
        state = self._approvals.decide(workflow_id, command, principal)
        if state.status == WorkflowStatus.DENIED:
            try:
                state = self._finalization.run(state)
            except Exception as exc:
                state = self._finalization.fail_closed(
                    state,
                    exc,
                    stage=WorkflowStage.FINAL_RESPONSE_AUDIT,
                )
            return self._states.response(state)
        if self._approvals.has_pending(state):
            return self._states.response(state)
        if not self._approvals.all_approved(state):
            state = self._states.set_status(
                state,
                WorkflowStatus.DENIED,
                error_code="approval_not_satisfied",
            )
            state = self._finalization.run(state)
            return self._states.response(state)

        try:
            state = self._execution.run(state)
            state = self._finalization.run(state)
        except Exception as exc:
            state = self._finalization.fail_closed(
                state,
                exc,
                stage=(
                    WorkflowStage.FINAL_RESPONSE_AUDIT
                    if state.current_stage == WorkflowStage.RETRY_RECOVERY
                    else WorkflowStage.RETRY_RECOVERY
                ),
            )
        return self._states.response(state)

    def get_response(self, workflow_id: str) -> GovernedResponse:
        """Return the complete response for an existing workflow.

        Raises:
            UnknownWorkflowError: If the workflow does not exist.
        """
        return self._states.response(self._states.require(workflow_id))

    def get_summary(self, workflow_id: str) -> WorkflowSummary:
        """Return the compact summary for an existing workflow.

        Raises:
            UnknownWorkflowError: If the workflow does not exist.
        """
        return self._states.summary(self._states.require(workflow_id))

    def audit_trace(self, workflow_id: str) -> AuditTrace:
        """Return the verified keyed audit chain for an existing workflow.

        Raises:
            UnknownWorkflowError: If the workflow does not exist.
            AuditIntegrityError: If sequence, identity, linkage, or event hashes fail.
        """
        self._states.require(workflow_id)
        return self._runtime.audit.trace(workflow_id)
