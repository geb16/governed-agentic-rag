"""Resumable sequential acquisition with one permitted pre-acceptance rerun."""

from __future__ import annotations

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.application.ports import (
    AttemptJournalStore,
    RawExecutionStore,
    SystemRunner,
)
from paired_agent_evaluation.domain.executions import AttemptState, Condition, ScheduledExecution
from paired_agent_evaluation.domain.observations import AcceptanceStatus, RawExecution


class AcquisitionRunner:
    def __init__(
        self,
        *,
        runners: dict[Condition, SystemRunner],
        store: RawExecutionStore,
        attempts: AttemptJournalStore,
        max_pre_acceptance_attempts: int,
    ) -> None:
        self._runners = runners
        self._store = store
        self._attempts = attempts
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
            prior_attempts = self._attempts.list(identity)
            for expected_attempt, journal in enumerate(prior_attempts, start=1):
                if journal.record.observation_id != identity:
                    raise RuntimeError(f"Attempt journal identity mismatch for {identity}")
                if journal.record.attempt != expected_attempt:
                    raise RuntimeError(f"Attempt journal sequence mismatch for {identity}")
                if journal.record.state != AttemptState.PRE_ACCEPTANCE_FAILED:
                    raise RuntimeError(
                        f"Refusing to rerun indeterminate attempt for {identity}: "
                        f"{journal.record.state.value}"
                    )
            if len(prior_attempts) >= self._max_attempts:
                raise RuntimeError(f"Pre-acceptance attempt limit reached for {identity}")
            first_attempt = len(prior_attempts) + 1
            for attempt in range(first_attempt, self._max_attempts + 1):
                journal = self._attempts.begin(identity, attempt)
                execution = self._runners[scheduled.key.condition].execute(
                    by_case[scheduled.key.case_id],
                    scheduled,
                    journal.workspace,
                    acceptance=journal,
                )
                if execution.request_accepted != journal.accepted:
                    raise RuntimeError(f"Runner acceptance evidence mismatch for {identity}")
                if execution.acceptance == AcceptanceStatus.ACCEPTED:
                    break
                journal.mark_pre_acceptance_failed(execution.error_type)
            assert execution is not None
            self._store.write(execution)
            journal.mark_observation_persisted()
        return self._store.read_all()
