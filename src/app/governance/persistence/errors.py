"""Preserve compatibility imports for governance application-level errors.

New code should import these stable errors from ``app.governance.contracts``.
This module contains no persistence-specific exception definitions.
"""

from app.governance.contracts.errors import ApprovalValidationError, WorkflowConflictError

__all__ = ["ApprovalValidationError", "WorkflowConflictError"]
