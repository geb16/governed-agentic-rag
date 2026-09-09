from datetime import UTC, datetime

import pytest
from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournal,
    FilesystemAttemptJournalStore,
)

from paired_agent_evaluation.adapters.storage.filesystem import RawFilesystemStore
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import AttemptState, Condition
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


class SequencedRunner:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, case, scheduled, workspace, *, acceptance) -> RawExecution:
        self.calls += 1
        now = datetime.now(UTC)
        accepted = self.calls > 1
        if accepted:
            acceptance.mark_accepted()
        return RawExecution(
            key=scheduled.key,
            acceptance=AcceptanceStatus.ACCEPTED if accepted else AcceptanceStatus.INVALID,
            request_accepted=accepted,
            started_at=now,
            completed_at=now,
            latency_ms=1,
            request={"query": case.request.query},
            state_before=BusinessState(),
            state_after=BusinessState(),
        )


# Test to assert that the acquisition runner retries pre-acceptance once then resumes normally.
def test_acquisition_retries_pre_acceptance_once_and_resumes(tmp_path, answer_case) -> None:

    scheduled = next(
        item
        for item in build_schedule([answer_case], repetitions=1, seed=1)
        if item.key.condition == Condition.BASELINE
    )
    runner = SequencedRunner()
    store = RawFilesystemStore(tmp_path / "raw")
    acquisition = AcquisitionRunner(
        runners={Condition.BASELINE: runner},
        store=store,
        attempts=FilesystemAttemptJournalStore(tmp_path / "work"),
        max_pre_acceptance_attempts=2,
    )
    result = acquisition.run([scheduled], [answer_case])
    assert result[0].acceptance == AcceptanceStatus.ACCEPTED
    assert runner.calls == 2
    attempt_root = tmp_path / "work" / scheduled.key.observation_id
    assert FilesystemAttemptJournal.load(attempt_root / "attempt-1").record.state == (
        AttemptState.PRE_ACCEPTANCE_FAILED
    )
    assert FilesystemAttemptJournal.load(attempt_root / "attempt-2").record.state == (
        AttemptState.ACCEPTED_OBSERVATION_PERSISTED
    )
    acquisition.run([scheduled], [answer_case])
    assert runner.calls == 2


class InterruptedRunner:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, case, scheduled, workspace, *, acceptance) -> RawExecution:
        self.calls += 1
        acceptance.mark_accepted()
        raise KeyboardInterrupt


def test_acquisition_refuses_to_rerun_an_interrupted_accepted_attempt(
    tmp_path, answer_case
) -> None:
    """An accepted invocation without a raw record requires operator intervention."""
    scheduled = next(
        item
        for item in build_schedule([answer_case], repetitions=1, seed=1)
        if item.key.condition == Condition.BASELINE
    )
    runner = InterruptedRunner()
    acquisition = AcquisitionRunner(
        runners={Condition.BASELINE: runner},
        store=RawFilesystemStore(tmp_path / "raw"),
        attempts=FilesystemAttemptJournalStore(tmp_path / "work"),
        max_pre_acceptance_attempts=2,
    )

    with pytest.raises(KeyboardInterrupt):
        acquisition.run([scheduled], [answer_case])
    with pytest.raises(RuntimeError, match="Refusing to rerun indeterminate attempt"):
        acquisition.run([scheduled], [answer_case])

    assert runner.calls == 1
    attempt_root = tmp_path / "work" / scheduled.key.observation_id / "attempt-1"
    assert FilesystemAttemptJournal.load(attempt_root).record.state == AttemptState.ACCEPTED
