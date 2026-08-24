"""Manage durable workflow state and project caller-visible response views.

The service centralizes case validation, idempotency lookup, optimistic checkpoints,
usage accumulation, evidence aggregation, and response projection so runners do not
duplicate state mechanics.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.baseline.application.contracts import Usage
from app.governance.contracts import (
    ApprovalStatus,
    GovernedRequest,
    GovernedResponse,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
    WorkflowSummary,
)
from app.governance.orchestration.dependencies import WorkflowRuntime
from app.governance.orchestration.errors import (
    UnknownSyntheticCaseError,
    UnknownWorkflowError,
)


class WorkflowStateService:
    """Provide lifecycle operations over the injected workflow repository.

    Args:
        runtime: Injected business, workflow, audit, retrieval, and model identities.
    """

    def __init__(self, runtime: WorkflowRuntime) -> None:
        """Initialize state operations over the injected runtime ports."""
        self._runtime = runtime

    def create(self, request: GovernedRequest) -> WorkflowState:
        """Create a running workflow after validating its synthetic case.

        Raises:
            UnknownSyntheticCaseError: If the neutral case identity does not exist.
        """
        if not self._runtime.business_repository.case_exists(request.case_id):
            raise UnknownSyntheticCaseError(request.case_id)
        return self._runtime.workflows.create(
            WorkflowState(request=request, status=WorkflowStatus.RUNNING)
        )

    def require(self, workflow_id: str) -> WorkflowState:
        """Return a workflow or raise the stable not-found application error.

        Raises:
            UnknownWorkflowError: If the workflow identity is absent.
        """
        state = self._runtime.workflows.get(workflow_id)
        if state is None:
            raise UnknownWorkflowError(workflow_id)
        return state

    def find_by_request_id(self, request_id: str) -> WorkflowState | None:
        """Return a prior workflow for idempotent invocation replay, when present."""
        return self._runtime.workflows.get_by_request_id(request_id)

    def save_stage(
        self,
        state: WorkflowState,
        stage: WorkflowStage,
    ) -> WorkflowState:
        """Checkpoint a stage identity using optimistic concurrency.

        Returns:
            Persisted state with incremented version and trusted timestamp.
        """
        candidate = state.model_copy(
            update={"current_stage": stage, "updated_at": datetime.now(UTC)}
        )
        return self._runtime.workflows.update(
            candidate,
            expected_version=state.state_version,
        )

    def set_status(
        self,
        state: WorkflowState,
        status: WorkflowStatus,
        *,
        error_code: str | None = None,
    ) -> WorkflowState:
        """Persist a lifecycle status and optional stable error identity."""
        candidate = state.model_copy(update={"status": status, "error_code": error_code})
        return self._runtime.workflows.update(
            candidate,
            expected_version=state.state_version,
        )

    @staticmethod
    def add_usage(usage: Usage, input_tokens: int, output_tokens: int) -> Usage:
        """Return cumulative provider usage without mutating prior state."""
        return Usage(
            input_tokens=usage.input_tokens + input_tokens,
            output_tokens=usage.output_tokens + output_tokens,
        )

    def response(self, state: WorkflowState) -> GovernedResponse:
        """Project complete caller-visible state with evidence and audit count.

        Retrieved and tool-produced evidence are combined without exposing internal
        persistence rows or security configuration.
        """
        evidence = list(state.retrieval.evidence if state.retrieval else [])
        for call in state.tool_calls:
            evidence.extend(call.evidence)
        return GovernedResponse(
            workflow_id=state.workflow_id,
            request_id=state.request.request_id,
            case_id=state.request.case_id,
            trace_id=state.trace_id,
            status=state.status,
            current_stage=state.current_stage,
            state_version=state.state_version,
            answer=state.final.answer if state.final else None,
            classification=state.classification,
            proposal=state.proposal,
            risk=state.risk,
            approval_route=state.approval_route,
            approvals=state.approvals,
            recovery=state.recovery,
            tool_calls=state.tool_calls,
            evidence=evidence,
            retrieval_backend=self._runtime.retriever.backend_name,
            model=self._runtime.model_name,
            usage=state.usage,
            audit_event_count=len(self._runtime.audit.list_events(state.workflow_id)),
            error_code=state.error_code,
            created_at=state.created_at,
        )

    def summary(self, state: WorkflowState) -> WorkflowSummary:
        """Project the minimal polling and approval view of a workflow."""
        return WorkflowSummary(
            workflow_id=state.workflow_id,
            request_id=state.request.request_id,
            status=state.status,
            current_stage=state.current_stage,
            state_version=state.state_version,
            proposal_digest=(
                state.approval_route.proposal_digest if state.approval_route else None
            ),
            pending_roles=[
                item.role for item in state.approvals if item.status == ApprovalStatus.PENDING
            ],
        )
