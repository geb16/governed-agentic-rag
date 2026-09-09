from datetime import UTC, datetime

from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournalStore,
)
from paired_agent_evaluation.adapters.storage.filesystem import RawFilesystemStore
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.application.ports import AcceptanceRecorder
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import Condition
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


class SequencedRunner:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self, case, scheduled, workspace, *, acceptance: AcceptanceRecorder
    ) -> RawExecution:
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
    acquisition.run([scheduled], [answer_case])
    assert runner.calls == 2
