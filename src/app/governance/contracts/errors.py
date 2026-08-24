"""Stable application errors shared by governance ports and inbound adapters."""


class ApprovalValidationError(ValueError):
    """Approval data is expired, already decided, or not bound to the proposal."""


class WorkflowConflictError(RuntimeError):
    """Optimistic concurrency or state-transition validation rejected a write."""
