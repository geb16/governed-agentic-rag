"""Adapt the workflow repository port to focused SQLite stores."""

from pathlib import Path

from app.governance.contracts import WorkflowState
from app.governance.persistence.approval_store import ApprovalStore
from app.governance.persistence.connection import SqliteConnectionFactory
from app.governance.persistence.workflow_store import WorkflowStateStore


class SqliteGovernanceRepository:
    """Provide one repository façade over workflow-state and approval stores.

    Args:
        database_path: Shared SQLite database containing business, workflow, and
            audit records for the pilot.
    """

    def __init__(self, database_path: Path) -> None:
        """Initialize focused workflow and approval stores over one database."""
        connections = SqliteConnectionFactory(database_path)
        self._workflows = WorkflowStateStore(connections)
        self._approvals = ApprovalStore(connections)

    def initialize(self) -> None:
        """Create or validate the governed workflow schema."""
        self._workflows.initialize()

    def create(self, state: WorkflowState) -> WorkflowState:
        """Persist a new workflow aggregate."""
        return self._workflows.create(state)

    def get(self, workflow_id: str) -> WorkflowState | None:
        """Return a workflow by identity, or ``None`` when absent."""
        return self._workflows.get(workflow_id)

    def get_by_request_id(self, request_id: str) -> WorkflowState | None:
        """Return the workflow associated with an idempotent request ID."""
        return self._workflows.get_by_request_id(request_id)

    def update(self, state: WorkflowState, *, expected_version: int) -> WorkflowState:
        """Persist a valid state transition using optimistic concurrency."""
        return self._workflows.update(state, expected_version=expected_version)

    def pause_for_approvals(
        self,
        state: WorkflowState,
        *,
        expected_version: int,
    ) -> WorkflowState:
        """Atomically pause a running workflow and create role approvals."""
        return self._approvals.pause(state, expected_version=expected_version)

    def decide_approval(
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
        """Persist one role decision after transactional approval validation."""
        return self._approvals.decide(
            workflow_id=workflow_id,
            role=role,
            approved=approved,
            actor_id=actor_id,
            proposal_digest=proposal_digest,
            expected_version=expected_version,
            comment=comment,
        )

    def expire_pending_approvals(
        self,
        *,
        workflow_id: str,
        expected_version: int,
    ) -> WorkflowState:
        """Deny a workflow and expire its still-pending role approvals."""
        return self._approvals.expire_pending_approvals(
            workflow_id=workflow_id,
            expected_version=expected_version,
        )
