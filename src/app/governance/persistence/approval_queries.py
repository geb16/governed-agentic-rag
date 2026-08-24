"""Provide focused SQLite queries and validation for approval decisions.

The helpers operate inside caller-owned transactions. They centralize stale-state,
proposal-binding, role, duplicate-decision, and expiration checks so every approval
write applies the same fail-closed rules.
"""

import sqlite3
from datetime import datetime
from typing import cast

from app.governance.contracts import (
    ApprovalRecord,
    ApprovalStatus,
    ApprovalValidationError,
    WorkflowConflictError,
    WorkflowStatus,
)


def workflow_row(
    connection: sqlite3.Connection,
    workflow_id: str,
) -> sqlite3.Row:
    """Load the workflow fields required to decide an approval.

    Args:
        connection: Active SQLite transaction connection.
        workflow_id: Governed workflow identity.

    Returns:
        The matching workflow row.

    Raises:
        KeyError: If the workflow does not exist.
    """
    row = connection.execute(
        """
        SELECT state_json, state_version, status
        FROM governance_workflows WHERE workflow_id = ?
        """,
        (workflow_id,),
    ).fetchone()
    if row is None:
        raise KeyError(workflow_id)
    return cast(sqlite3.Row, row)


def validate_active(
    row: sqlite3.Row,
    workflow_id: str,
    expected_version: int,
) -> None:
    """Reject an approval against a stale or non-pending workflow.

    Args:
        row: Workflow row loaded in the active write transaction.
        workflow_id: Workflow identity used in a stable error message.
        expected_version: Version supplied by the caller for optimistic concurrency.

    Raises:
        WorkflowConflictError: If version or workflow status is not current.
    """
    if (
        int(row["state_version"]) != expected_version
        or row["status"] != WorkflowStatus.PENDING_APPROVAL.value
    ):
        raise WorkflowConflictError(f"Stale or inactive workflow {workflow_id}")


def approval_row(
    connection: sqlite3.Connection,
    workflow_id: str,
    role: str,
) -> sqlite3.Row:
    """Load the role-specific approval record for a workflow.

    Raises:
        ApprovalValidationError: If the role is not required by the approval route.
    """
    row = connection.execute(
        "SELECT * FROM governance_approvals WHERE workflow_id = ? AND role = ?",
        (workflow_id, role),
    ).fetchone()
    if row is None:
        raise ApprovalValidationError("Role is not required for this workflow")
    return cast(sqlite3.Row, row)


def validate_approval(
    row: sqlite3.Row,
    proposal_digest: str,
    decided_at: datetime,
) -> None:
    """Validate proposal binding, pending status, and expiration.

    Args:
        row: Role-specific approval row locked by the caller's transaction.
        proposal_digest: Digest submitted with the approval command.
        decided_at: Trusted server timestamp for the decision.

    Raises:
        ApprovalValidationError: If the proposal differs, the record was already
            decided, or the approval window has expired.
    """
    if row["proposal_digest"] != proposal_digest:
        raise ApprovalValidationError("Approval is not bound to this proposal")
    if row["status"] != ApprovalStatus.PENDING.value:
        raise ApprovalValidationError("Approval has already been decided")
    if decided_at > datetime.fromisoformat(row["expires_at"]):
        raise ApprovalValidationError("Approval request has expired")


def list_approvals(
    connection: sqlite3.Connection,
    workflow_id: str,
) -> list[ApprovalRecord]:
    """Return all workflow approvals in deterministic role order.

    Args:
        connection: Active SQLite connection.
        workflow_id: Workflow whose approval records are requested.

    Returns:
        Validated approval contracts ordered by role.
    """
    rows = connection.execute(
        "SELECT * FROM governance_approvals WHERE workflow_id = ? ORDER BY role",
        (workflow_id,),
    ).fetchall()
    return [
        ApprovalRecord(
            approval_id=row["approval_id"],
            role=row["role"],
            status=row["status"],
            proposal_digest=row["proposal_digest"],
            actor_id=row["actor_id"],
            comment=row["comment"],
            decided_at=row["decided_at"],
        )
        for row in rows
    ]
