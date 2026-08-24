"""Resolve composed workflow and trusted approval-principal dependencies.

Caller payloads never provide principal identity or roles. The authenticated API
credential maps to server-side governance settings at this pilot boundary.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.governance.contracts import ApprovalPrincipal
from app.governance.orchestration import GovernedWorkflow
from app.governance.security import GovernanceSecuritySettings


def get_workflow(request: Request) -> GovernedWorkflow:
    """Return the composed workflow or fail readiness at the request boundary.

    Args:
        request: Active FastAPI request containing application state.

    Returns:
        The initialized governed workflow use case.

    Raises:
        HTTPException: With status 503 when provider-backed composition is absent.
    """
    workflow: GovernedWorkflow | None = request.app.state.governed_workflow
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Governed workflow is not configured",
        )
    return workflow


WorkflowDependency = Annotated[GovernedWorkflow, Depends(get_workflow)]


def get_approval_principal(request: Request) -> ApprovalPrincipal:
    """Return the server-configured principal bound to the authenticated API key.

    Args:
        request: Authenticated FastAPI request containing governance settings.

    Returns:
        Trusted subject and role bindings unavailable to caller JSON.

    Raises:
        HTTPException: With status 403 when the configured principal has no roles.
    """
    settings: GovernanceSecuritySettings = request.app.state.governance_security
    if not settings.approval_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authenticated principal has no approval roles",
        )
    return ApprovalPrincipal(
        subject_id=settings.approval_principal_id,
        roles=frozenset(settings.approval_roles),
    )


ApprovalPrincipalDependency = Annotated[ApprovalPrincipal, Depends(get_approval_principal)]
