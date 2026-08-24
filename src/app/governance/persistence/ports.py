"""Declare the application port for durable governed workflow state."""

from typing import Protocol

from app.governance.contracts import WorkflowState


class WorkflowRepository(Protocol):
    """Persist governed state and role-bound approvals with optimistic locking."""

    def initialize(self) -> None:
        """Create or validate the persistence schema."""
        ...

    def create(self, state: WorkflowState) -> WorkflowState:
        """Persist a new workflow and return its unchanged state."""
        ...

    def get(self, workflow_id: str) -> WorkflowState | None:
        """Return a workflow by identity, or ``None`` when it is absent."""
        ...

    def get_by_request_id(self, request_id: str) -> WorkflowState | None:
        """Return the workflow bound to an idempotent request identity."""
        ...

    def update(self, state: WorkflowState, *, expected_version: int) -> WorkflowState:
        """Compare-and-swap a workflow and return its incremented state."""
        ...

    def pause_for_approvals(
        self,
        state: WorkflowState,
        *,
        expected_version: int,
    ) -> WorkflowState:
        """Atomically pause a workflow and create its required approvals."""
        ...

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
        """Atomically persist one authenticated, proposal-bound decision."""
        ...
