"""Port and repository adapter for deterministic evaluation fault injection."""

from __future__ import annotations

from typing import Protocol

from app.domain.repositories import SyntheticRepository
from app.domain.support import ConsumedFault


class FaultInjector(Protocol):
    """Consume deterministic, case-scoped tool failures."""

    def consume(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        """Return the next planned failure, if one remains."""
        ...


class RepositoryFaultInjector:
    """Delegate deterministic failure consumption to synthetic persistence."""

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def consume(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        """Return the next repository-backed failure for the case and tool."""
        return self._repository.consume_fault(case_id, tool_name)
