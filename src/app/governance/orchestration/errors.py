"""Define stable orchestration failures independent of HTTP and providers."""

from app.governance.contracts import WorkflowStage, WorkflowState


class ApprovalAuthorizationError(PermissionError):
    """Authenticated principal does not hold the requested approval role."""


class UnknownWorkflowError(KeyError):
    """Requested workflow ID does not exist."""


class UnknownSyntheticCaseError(KeyError):
    """Requested synthetic evaluation case does not exist."""


class StageExecutionError(RuntimeError):
    """Preserve the stage, cause, and last durable state of a planning failure.

    Attributes:
        stage: Stable workflow stage in which the failure occurred.
        cause: Original exception retained for internal diagnostics.
        state: Last known state used by fail-closed finalization.
    """

    def __init__(
        self,
        stage: WorkflowStage,
        cause: Exception,
        state: WorkflowState,
    ) -> None:
        """Initialize a stage-aware wrapper around the original failure."""
        super().__init__(f"Governance stage {stage.value} failed")
        self.stage = stage
        self.cause = cause
        self.state = state
