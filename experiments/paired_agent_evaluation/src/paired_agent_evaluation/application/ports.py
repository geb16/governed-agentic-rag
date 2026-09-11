"""Define structural ports between application policy and external adapters.

The protocols keep acquisition independent of system and storage implementations,
including the durable acceptance signal used to prevent unsafe invocation retries.

References:
    [1] Alistair Cockburn, "Hexagonal Architecture."
        https://alistair.cockburn.us/hexagonal-architecture
    [2] Python Enhancement Proposal 544, "Protocols: Structural subtyping."
        https://peps.python.org/pep-0544/
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.executions import AttemptRecord, ScheduledExecution
from paired_agent_evaluation.domain.observations import RawExecution


class AcceptanceRecorder(Protocol):
    """Records when provider acceptance makes an invocation unsafe to retry."""

    @property
    def accepted(self) -> bool: ...

    def mark_accepted(self) -> None: ...


class AttemptJournal(AcceptanceRecorder, Protocol):
    """Exposes durable state and workspace for one acquisition attempt."""

    @property
    def workspace(self) -> Path: ...

    @property
    def record(self) -> AttemptRecord: ...

    def mark_pre_acceptance_failed(self, error_type: str | None) -> None: ...

    def mark_observation_persisted(self) -> None: ...


class AttemptJournalStore(Protocol):
    """Creates and enumerates attempt journals for an observation."""

    def list(self, observation_id: str) -> Sequence[AttemptJournal]: ...

    def begin(self, observation_id: str, attempt: int) -> AttemptJournal: ...


class SystemRunner(Protocol):
    """Executes scheduled cases against one experiment condition."""

    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution:
        """Executes a case and records provider acceptance before risky work."""
        ...


class RawExecutionStore(Protocol):
    """Persists and retrieves raw executions by observation identity."""

    def exists(self, observation_id: str) -> bool:
        """Reports whether an observation has already been persisted."""
        ...

    def write(self, execution: RawExecution) -> Path:
        """Persists an execution and returns its artifact path."""
        ...

    def read_all(self) -> list[RawExecution]:
        """Returns every persisted raw execution in stable adapter order."""
        ...
