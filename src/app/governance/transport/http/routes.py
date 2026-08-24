"""Map authenticated Phase 4 HTTP operations to the governed use case.

Routes validate transport contracts and translate stable application failures into
bounded HTTP responses. Business, policy, persistence, and provider behavior remain
outside this adapter. The router-level API-key dependency protects every operation.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.audit.schemas import AuditTrace
from app.core.security import require_api_key
from app.governance.contracts import (
    ApprovalCommand,
    ApprovalValidationError,
    GovernedRequest,
    GovernedResponse,
    WorkflowConflictError,
    WorkflowSummary,
)
from app.governance.orchestration.errors import (
    ApprovalAuthorizationError,
    UnknownSyntheticCaseError,
    UnknownWorkflowError,
)
from app.governance.transport.http.dependencies import (
    ApprovalPrincipalDependency,
    WorkflowDependency,
)

WorkflowId = Annotated[
    str,
    Path(min_length=4, max_length=80, pattern=r"^wf_[a-zA-Z0-9_-]+$"),
]

router = APIRouter(
    prefix="/governed",
    tags=["governed-workflow"],
    dependencies=[Depends(require_api_key)],
)


@router.post("/invoke", response_model=GovernedResponse)
def invoke(
    payload: GovernedRequest,
    workflow: WorkflowDependency,
) -> GovernedResponse:
    """Create or idempotently replay a governed workflow.

    Args:
        payload: Strict neutral request contract.
        workflow: Composed use case resolved from application state.

    Returns:
        Current workflow response, including a prior result for identical replay.

    Raises:
        HTTPException: With status 404 for an unknown synthetic case or 409 when a
            request ID is reused with different immutable input.
    """
    try:
        return workflow.invoke(payload)
    except UnknownSyntheticCaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Synthetic case not found",
        ) from exc
    except WorkflowConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/{workflow_id}/approval", response_model=GovernedResponse)
def decide_approval(
    workflow_id: WorkflowId,
    command: ApprovalCommand,
    workflow: WorkflowDependency,
    principal: ApprovalPrincipalDependency,
) -> GovernedResponse:
    """Apply one authenticated, role-bound approval decision.

    Args:
        workflow_id: Validated governed workflow identity.
        command: Digest-bound decision and expected state version.
        workflow: Composed governed use case.
        principal: Server-configured authenticated subject and roles.

    Returns:
        Updated or resumed workflow response.

    Raises:
        HTTPException: With status 404 when absent, 403 when the principal lacks the
            role, or 409 for stale, expired, repeated, or mismatched decisions.
    """
    try:
        return workflow.approve(workflow_id, command, principal)
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        ) from exc
    except (WorkflowConflictError, ApprovalValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ApprovalAuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authenticated principal is not authorized for this approval role",
        ) from exc


@router.get("/{workflow_id}", response_model=GovernedResponse)
def get_workflow(
    workflow_id: WorkflowId,
    workflow: WorkflowDependency,
) -> GovernedResponse:
    """Return the complete caller-visible workflow state.

    Raises:
        HTTPException: With status 404 when the workflow does not exist.
    """
    try:
        return workflow.get_response(workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        ) from exc


@router.get("/{workflow_id}/summary", response_model=WorkflowSummary)
def get_summary(
    workflow_id: WorkflowId,
    workflow: WorkflowDependency,
) -> WorkflowSummary:
    """Return a compact polling and approval summary for a workflow.

    Raises:
        HTTPException: With status 404 when the workflow does not exist.
    """
    try:
        return workflow.get_summary(workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        ) from exc


@router.get("/{workflow_id}/audit", response_model=AuditTrace)
def get_audit_trace(
    workflow_id: WorkflowId,
    workflow: WorkflowDependency,
) -> AuditTrace:
    """Return the ordered audit trace after verifying its keyed hash chain.

    Raises:
        HTTPException: With status 404 when the workflow does not exist.
    """
    try:
        return workflow.audit_trace(workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        ) from exc
