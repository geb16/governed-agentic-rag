"""Ports separating the experiment core from systems, graders, and storage."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.observations import RawExecution


class SystemRunner(Protocol):
    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
    ) -> RawExecution: ...


class RawExecutionStore(Protocol):
    def exists(self, observation_id: str) -> bool: ...

    def write(self, execution: RawExecution) -> Path: ...

    def read_all(self) -> list[RawExecution]: ...
