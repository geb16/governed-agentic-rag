"""Persist and validate the durable governed workflow aggregate.

The store owns schema initialization, idempotency lookup, optimistic concurrency,
and allowed lifecycle transitions. Approval row mutations remain in the focused
approval store.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.governance.contracts import WorkflowConflictError, WorkflowState, WorkflowStatus
from app.governance.persistence.connection import SqliteConnectionFactory
from app.governance.persistence.schema import GOVERNANCE_SCHEMA_VERSION, SCHEMA


class WorkflowStateStore:
    """Store workflow aggregates as validated JSON plus indexed lifecycle columns.

    Args:
        connections: Factory that owns or joins SQLite transaction connections.
    """

    def __init__(self, connections: SqliteConnectionFactory) -> None:
        """Initialize aggregate persistence with transaction-aware connections."""
        self._connections = connections

    def initialize(self) -> None:
        """Create tables and reject an unsupported governance schema version.

        Raises:
            RuntimeError: If persisted schema metadata differs from the code version.
            OSError: If the database parent directory cannot be created.
        """
        self._connections.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connections.connect() as connection:
            connection.executescript(SCHEMA)
            row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'governance_schema_version'"
            ).fetchone()
            if row is not None and int(row["value"]) != GOVERNANCE_SCHEMA_VERSION:
                raise RuntimeError("Unsupported governance schema version")
            connection.execute(
                "INSERT OR IGNORE INTO schema_metadata(key, value) VALUES (?, ?)",
                ("governance_schema_version", str(GOVERNANCE_SCHEMA_VERSION)),
            )

    def create(self, state: WorkflowState) -> WorkflowState:
        """Persist a new workflow with unique request and trace identities.

        Args:
            state: Newly initialized workflow aggregate.

        Returns:
            The unchanged persisted state.

        Raises:
            sqlite3.IntegrityError: If an identity already exists or the case is absent.
        """
        with self._connections.connect() as connection:
            connection.execute(
                """
                INSERT INTO governance_workflows(
                    workflow_id, request_id, case_id, trace_id, status,
                    current_stage, state_version, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.workflow_id,
                    state.request.request_id,
                    state.request.case_id,
                    state.trace_id,
                    state.status.value,
                    state.current_stage.value,
                    state.state_version,
                    state.model_dump_json(),
                    state.created_at.isoformat(),
                    state.updated_at.isoformat(),
                ),
            )
        return state

    def get(self, workflow_id: str) -> WorkflowState | None:
        """Load and validate a workflow aggregate by workflow identity."""
        with self._connections.connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM governance_workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        return WorkflowState.model_validate_json(row["state_json"]) if row else None

    def get_by_request_id(self, request_id: str) -> WorkflowState | None:
        """Return the workflow bound to an idempotency key, when present.

        This lookup enables replay without repeated provider, tool, or audit work.
        """
        with self._connections.connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM governance_workflows WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return WorkflowState.model_validate_json(row["state_json"]) if row else None

    def update(self, state: WorkflowState, *, expected_version: int) -> WorkflowState:
        """Validate a transition and persist it with compare-and-swap semantics.

        Args:
            state: Desired aggregate state before version increment.
            expected_version: Durable version the caller previously observed.

        Returns:
            Persisted state with incremented version and updated timestamp.

        Raises:
            WorkflowConflictError: If the transition is invalid or state is stale.
        """
        updated = state.model_copy(
            update={
                "state_version": expected_version + 1,
                "updated_at": datetime.now(UTC),
            }
        )
        with self._connections.connect() as connection:
            current = connection.execute(
                "SELECT status FROM governance_workflows WHERE workflow_id = ?",
                (updated.workflow_id,),
            ).fetchone()
            if current is not None:
                self._validate_status_transition(
                    WorkflowStatus(current["status"]),
                    updated.status,
                )
            result = connection.execute(
                """
                UPDATE governance_workflows
                SET status = ?, current_stage = ?, state_version = ?,
                    state_json = ?, updated_at = ?
                WHERE workflow_id = ? AND state_version = ?
                """,
                (
                    updated.status.value,
                    updated.current_stage.value,
                    updated.state_version,
                    updated.model_dump_json(),
                    updated.updated_at.isoformat(),
                    updated.workflow_id,
                    expected_version,
                ),
            )
            if result.rowcount != 1:
                raise WorkflowConflictError(f"Stale workflow state for {state.workflow_id}")
        return updated

    @staticmethod
    def _validate_status_transition(
        current: WorkflowStatus,
        target: WorkflowStatus,
    ) -> None:
        """Reject invalid terminal-state and approval-state transitions.

        Terminal workflows cannot be reopened, and approval resumption is available
        only from ``pending_approval``.
        """
        allowed = {
            WorkflowStatus.INITIALIZED: {WorkflowStatus.INITIALIZED, WorkflowStatus.RUNNING},
            WorkflowStatus.RUNNING: {
                WorkflowStatus.RUNNING,
                WorkflowStatus.PENDING_APPROVAL,
                WorkflowStatus.CLARIFICATION_REQUIRED,
                WorkflowStatus.DENIED,
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
            },
            WorkflowStatus.PENDING_APPROVAL: {
                WorkflowStatus.PENDING_APPROVAL,
                WorkflowStatus.RUNNING,
                WorkflowStatus.DENIED,
                WorkflowStatus.FAILED,
            },
            WorkflowStatus.CLARIFICATION_REQUIRED: {
                WorkflowStatus.CLARIFICATION_REQUIRED,
                WorkflowStatus.FAILED,
            },
            WorkflowStatus.DENIED: {WorkflowStatus.DENIED, WorkflowStatus.FAILED},
            WorkflowStatus.COMPLETED: {WorkflowStatus.COMPLETED},
            WorkflowStatus.FAILED: {WorkflowStatus.FAILED},
        }
        if target not in allowed[current]:
            raise WorkflowConflictError(
                f"Invalid workflow status transition: {current.value} -> {target.value}"
            )
