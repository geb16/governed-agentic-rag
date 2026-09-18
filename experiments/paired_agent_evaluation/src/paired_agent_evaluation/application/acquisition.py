"""Runs resumable sequential acquisition with fail-closed retries.

Persisted observations are skipped when a run resumes. An incomplete observation
may continue only after every prior attempt records a confirmed pre-acceptance
failure; accepted or indeterminate attempts require operator intervention.
"""

from __future__ import annotations

from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.application.ports import (
    AttemptJournal,
    AttemptJournalStore,
    RawExecutionStore,
    SystemRunner,
)
from paired_agent_evaluation.domain.executions import AttemptState, Condition, ScheduledExecution
from paired_agent_evaluation.domain.observations import AcceptanceStatus, RawExecution


class AcquisitionRunner:
    """Coordinates system execution, attempt journals, and raw observations.

    Args:
        runners: System adapter selected by experiment condition.
        store: Persistence boundary for completed raw observations.
        attempts: Persistence boundary for retry-relevant attempt states.
        max_pre_acceptance_attempts: Maximum attempts allowed per observation.
    """

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
        """Acquires every missing observation in schedule order.

        Before retrying, the method validates prior journal identity, numbering,
        and state. Each new execution must agree with its journal about provider
        acceptance. The raw observation is stored before its attempt is marked
        terminal, allowing completed observations to be skipped on later runs.

        Args:
            schedule: Ordered executions to acquire.
            cases: Evaluation cases referenced by the schedule.

        Returns:
            All raw observations currently available from the configured store.

        Raises:
            KeyError: If a schedule entry references an unknown case or condition.
            RuntimeError: If prior journals are inconsistent or indeterminate,
                the attempt limit is exhausted, or acceptance evidence disagrees.
        """
        by_case = {case.case_id: case for case in cases}
        for scheduled in schedule:
            identity = scheduled.key.observation_id
            if self._store.exists(identity):
                continue
            execution: RawExecution | None = None
            prior_attempts = self._attempts.list(identity)
            for expected_attempt, prior_journal in enumerate(prior_attempts, start=1):
                if prior_journal.record.observation_id != identity:
                    raise RuntimeError(f"Attempt journal identity mismatch for {identity}")
                if prior_journal.record.attempt != expected_attempt:
                    raise RuntimeError(f"Attempt journal sequence mismatch for {identity}")
                if prior_journal.record.state != AttemptState.PRE_ACCEPTANCE_FAILED:
                    raise RuntimeError(
                        f"Refusing to rerun indeterminate attempt for {identity}: "
                        f"{prior_journal.record.state.value}"
                    )
            if len(prior_attempts) >= self._max_attempts:
                raise RuntimeError(f"Pre-acceptance attempt limit reached for {identity}")
            first_attempt = len(prior_attempts) + 1
            journal: AttemptJournal | None = None
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
            if execution is None or journal is None:
                raise RuntimeError(f"No acquisition attempt was made for {identity}")
            self._store.write(execution)
            journal.mark_observation_persisted()
        return self._store.read_all()
