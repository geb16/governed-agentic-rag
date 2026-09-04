"""Resumable sequential acquisition with one permitted pre-acceptance rerun."""

from __future__ import annotations

from pathlib import Path

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.application.ports import RawExecutionStore, SystemRunner
from paired_agent_evaluation.domain.executions import Condition, ScheduledExecution
from paired_agent_evaluation.domain.observations import AcceptanceStatus, RawExecution


class AcquisitionRunner:
    def __init__(
        self,
        *,
        runners: dict[Condition, SystemRunner],
        store: RawExecutionStore,
        workspace: Path,
        max_pre_acceptance_attempts: int,
    ) -> None:
        self._runners = runners
        self._store = store
        self._workspace = workspace
        self._max_attempts = max_pre_acceptance_attempts

    def run(
        self,
        schedule: list[ScheduledExecution],
        cases: list[EvaluationCase],
    ) -> list[RawExecution]:
        by_case = {case.case_id: case for case in cases}
        for scheduled in schedule:
            identity = scheduled.key.observation_id
            if self._store.exists(identity):
                continue
            execution: RawExecution | None = None
            observation_workspace = self._workspace / identity
            prior_attempts = list(observation_workspace.glob("attempt-*"))
            if len(prior_attempts) >= self._max_attempts:
                raise RuntimeError(f"Pre-acceptance attempt limit reached for {identity}")
            first_attempt = len(prior_attempts) + 1
            for attempt in range(first_attempt, self._max_attempts + 1):
                attempt_root = self._workspace / identity / f"attempt-{attempt}"
                attempt_root.mkdir(parents=True, exist_ok=False)
                execution = self._runners[scheduled.key.condition].execute(
                    by_case[scheduled.key.case_id],
                    scheduled,
                    attempt_root,
                )
                if execution.acceptance == AcceptanceStatus.ACCEPTED:
                    break
            assert execution is not None
            self._store.write(execution)
        return self._store.read_all()
