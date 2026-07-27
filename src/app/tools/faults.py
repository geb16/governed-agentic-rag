from __future__ import annotations

from typing import Protocol

from app.persistence.models import ConsumedFault
from app.persistence.repository import SyntheticRepository


# This class defines a protocol for fault injectors, which are responsible for
# consuming deterministic, case-scoped fault plans from shared state.
class FaultInjector(Protocol):
    def consume(self, case_id: str, tool_name: str) -> ConsumedFault | None: ...


class RepositoryFaultInjector:
    """
    Consumes deterministic, case-scoped fault plans from shared state.

    """

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def consume(self, case_id: str, tool_name: str) -> ConsumedFault | None:
        return self._repository.consume_fault(case_id, tool_name)
