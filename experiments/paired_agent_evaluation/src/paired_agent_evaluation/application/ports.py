"""Ports separating the experiment core from systems, graders, and storage."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.executions import AttemptRecord, ScheduledExecution
from paired_agent_evaluation.domain.observations import RawExecution


class AcceptanceRecorder(Protocol):
    """Durably record when rerunning an invocation becomes unsafe."""

    @property
    def accepted(self) -> bool: ...

    def mark_accepted(self) -> None: ...


class AttemptJournal(AcceptanceRecorder, Protocol):
    """Expose one durable attempt without binding policy to a storage adapter."""

    @property
    def workspace(self) -> Path: ...

    @property
    def record(self) -> AttemptRecord: ...

    def mark_pre_acceptance_failed(self, error_type: str | None) -> None: ...

    def mark_observation_persisted(self) -> None: ...


class AttemptJournalStore(Protocol):
    """Create and enumerate journals for a scheduled observation."""

    def list(self, observation_id: str) -> Sequence[AttemptJournal]: ...

    def begin(self, observation_id: str, attempt: int) -> AttemptJournal: ...


class SystemRunner(Protocol):
    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution: ...


class RawExecutionStore(Protocol):
    def exists(self, observation_id: str) -> bool: ...

    def write(self, execution: RawExecution) -> Path: ...

    def read_all(self) -> list[RawExecution]: ...
