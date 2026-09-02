"""Persist approval pauses and decisions with optimistic concurrency.

Each operation uses ``BEGIN IMMEDIATE`` so workflow state and role-bound approval
records change atomically. Validation occurs within the same write transaction to
prevent stale, expired, repeated, or proposal-substituted decisions.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from app.audit.sqlite.transaction import begin_immediate
from app.governance.contracts import (
    ApprovalRecord,
    ApprovalStatus,
    ApprovalValidationError,
    WorkflowConflictError,
    WorkflowState,
    WorkflowStatus,
)
from app.governance.persistence.approval_queries import (
    approval_row,
    list_approvals,
    validate_active,
    validate_approval,
    workflow_row,
)
from app.governance.persistence.connection import SqliteConnectionFactory


class ApprovalStore:
    """Own transactional persistence for human-approval lifecycle changes.

    Args:
        connections: Factory that joins an ambient unit of work when one exists.
    """

    def __init__(self, connections: SqliteConnectionFactory) -> None:
        """Initialize approval persistence with a transaction-aware connection factory."""
        self._connections = connections

    def pause(
        self,
        state: WorkflowState,
        *,
        expected_version: int,
    ) -> WorkflowState:
        """Persist a pending record for every role required by the approval route.

        Args:
            state: Running workflow containing a complete, expiring approval route.
            expected_version: Current durable version used for compare-and-swap.

        Returns:
            The incremented workflow in ``pending_approval`` status.

        Raises:
            ApprovalValidationError: If the route lacks roles, digest, or expiry.
            WorkflowConflictError: If the durable workflow is stale or not running.
            sqlite3.Error: If the atomic persistence operation fails.
        """
        route = state.approval_route
        if route is None or route.expires_at is None or not route.required_roles:
            raise ApprovalValidationError("Approval route is incomplete")
        records = [
            ApprovalRecord(
                approval_id=f"approval_{uuid4().hex}",
                role=role,
                status=ApprovalStatus.PENDING,
                proposal_digest=route.proposal_digest,
            )
            for role in route.required_roles
        ]
        updated = state.model_copy(
            update={
                "status": WorkflowStatus.PENDING_APPROVAL,
                "approvals": records,
                "state_version": expected_version + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        with self._connections.connect() as connection:
            begin_immediate(connection)
            self._assert_version(connection, state.workflow_id, expected_version)
            connection.executemany(
                """
                INSERT INTO governance_approvals(
                    approval_id, workflow_id, role, status, proposal_digest,
                    actor_id, comment, created_at, expires_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)
                """,
                [
                    (
                        item.approval_id,
                        state.workflow_id,
                        item.role,
                        item.status.value,
                        item.proposal_digest,
                        updated.updated_at.isoformat(),
                        route.expires_at.isoformat(),
                    )
                    for item in records
                ],
            )
            self._persist_paused(connection, updated, expected_version)
        return updated

    def decide(
        self,
        *,
        workflow_id: str,
        role: str,
        approved: bool,
        actor_id: str,
        proposal_digest: str,
        expected_version: int,
        comment: str | None,
    ) -> WorkflowState:
        """Persist one authenticated role decision and refresh aggregate approvals.

        Args:
            workflow_id: Pending workflow to update.
            role: Required role being decided.
            approved: Whether the trusted principal approved the proposal.
            actor_id: Pseudonymous identity of the authenticated principal.
            proposal_digest: Digest binding the decision to the exact proposal.
            expected_version: Current workflow version for optimistic concurrency.
            comment: Optional bounded reviewer rationale.

        Returns:
            Updated workflow state with the decision and incremented version.

        Raises:
            KeyError: If the workflow does not exist.
            ApprovalValidationError: If role, digest, status, or expiry is invalid.
            WorkflowConflictError: If workflow state changed concurrently.
            sqlite3.Error: If the atomic persistence operation fails.
        """
        decided_at = datetime.now(UTC)
        with self._connections.connect() as connection:
            begin_immediate(connection)
            workflow = workflow_row(connection, workflow_id)
            validate_active(workflow, workflow_id, expected_version)
            approval = approval_row(connection, workflow_id, role)
            validate_approval(approval, proposal_digest, decided_at)
            new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
            connection.execute(
                """
                UPDATE governance_approvals
                SET status = ?, actor_id = ?, comment = ?, decided_at = ?
                WHERE approval_id = ?
                """,
                (
                    new_status.value,
                    actor_id,
                    comment,
                    decided_at.isoformat(),
                    approval["approval_id"],
                ),
            )
            approvals = list_approvals(connection, workflow_id)
            state = WorkflowState.model_validate_json(workflow["state_json"])
            updated = state.model_copy(
                update={
                    "approvals": approvals,
                    "state_version": expected_version + 1,
                    "updated_at": decided_at,
                }
            )
            result = connection.execute(
                """
                UPDATE governance_workflows
                SET state_version = ?, state_json = ?, updated_at = ?
                WHERE workflow_id = ? AND state_version = ?
                """,
                (
                    updated.state_version,
                    updated.model_dump_json(),
                    updated.updated_at.isoformat(),
                    workflow_id,
                    expected_version,
                ),
            )
            if result.rowcount != 1:
                raise WorkflowConflictError(f"Stale workflow state for {workflow_id}")
        return updated

    def expire_pending_approvals(
        self,
        *,
        workflow_id: str,
        expected_version: int,
    ) -> WorkflowState:
        """Expire every still-pending role approval without transitioning status.

        Mirrors :meth:`decide`: only approval rows and the aggregate's ``approvals``
        and version change here. The caller applies the resulting terminal status
        transition through the same compare-and-swap ``update`` operation used
        everywhere else a workflow becomes ``denied``, keeping one validated path
        for status transitions.

        Args:
            workflow_id: Pending workflow whose approval window has elapsed.
            expected_version: Current workflow version for optimistic concurrency.

        Returns:
            Updated workflow state, still ``pending_approval``, with every
            previously pending approval marked ``expired``.

        Raises:
            KeyError: If the workflow does not exist.
            WorkflowConflictError: If the workflow is stale or no longer pending.
            sqlite3.Error: If the atomic persistence operation fails.
        """
        decided_at = datetime.now(UTC)
        with self._connections.connect() as connection:
            begin_immediate(connection)
            workflow = workflow_row(connection, workflow_id)
            validate_active(workflow, workflow_id, expected_version)
            connection.execute(
                """
                UPDATE governance_approvals
                SET status = ?, decided_at = ?
                WHERE workflow_id = ? AND status = ?
                """,
                (
                    ApprovalStatus.EXPIRED.value,
                    decided_at.isoformat(),
                    workflow_id,
                    ApprovalStatus.PENDING.value,
                ),
            )
            approvals = list_approvals(connection, workflow_id)
            state = WorkflowState.model_validate_json(workflow["state_json"])
            updated = state.model_copy(
                update={
                    "approvals": approvals,
                    "state_version": expected_version + 1,
                    "updated_at": decided_at,
                }
            )
            result = connection.execute(
                """
                UPDATE governance_workflows
                SET state_version = ?, state_json = ?, updated_at = ?
                WHERE workflow_id = ? AND state_version = ?
                """,
                (
                    updated.state_version,
                    updated.model_dump_json(),
                    updated.updated_at.isoformat(),
                    workflow_id,
                    expected_version,
                ),
            )
            if result.rowcount != 1:
                raise WorkflowConflictError(f"Stale workflow state for {workflow_id}")
        return updated

    @staticmethod
    def _assert_version(
        connection: sqlite3.Connection,
        workflow_id: str,
        expected_version: int,
    ) -> None:
        """Require the expected version of a currently running workflow."""
        row = connection.execute(
            "SELECT state_version, status FROM governance_workflows WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        if (
            row is None
            or int(row["state_version"]) != expected_version
            or row["status"] != WorkflowStatus.RUNNING.value
        ):
            raise WorkflowConflictError(f"Stale workflow state for {workflow_id}")

    @staticmethod
    def _persist_paused(
        connection: sqlite3.Connection,
        state: WorkflowState,
        expected_version: int,
    ) -> None:
        """Checkpoint pending status using a compare-and-swap update."""
        result = connection.execute(
            """
            UPDATE governance_workflows
            SET status = ?, state_version = ?, state_json = ?, updated_at = ?
            WHERE workflow_id = ? AND state_version = ?
            """,
            (
                state.status.value,
                state.state_version,
                state.model_dump_json(),
                state.updated_at.isoformat(),
                state.workflow_id,
                expected_version,
            ),
        )
        if result.rowcount != 1:
            raise WorkflowConflictError(f"Stale workflow state for {state.workflow_id}")
