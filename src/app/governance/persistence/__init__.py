"""Expose Phase 4 workflow persistence ports and the SQLite adapter.

Orchestration depends on ``WorkflowRepository`` and the unit-of-work boundary.
Concrete stores and SQL helpers remain internal implementation details.
"""

from app.governance.persistence.errors import (
    ApprovalValidationError,
    WorkflowConflictError,
)
from app.governance.persistence.ports import WorkflowRepository
from app.governance.persistence.repository import SqliteGovernanceRepository
from app.governance.persistence.unit_of_work import SqliteGovernanceUnitOfWork

__all__ = [
    "ApprovalValidationError",
    "SqliteGovernanceRepository",
    "SqliteGovernanceUnitOfWork",
    "WorkflowConflictError",
    "WorkflowRepository",
]
