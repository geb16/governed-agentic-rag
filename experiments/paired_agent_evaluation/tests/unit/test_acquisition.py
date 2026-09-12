"""Verify resumable acquisition and fail-closed retry behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.evaluation.dataset.models import EvaluationCase

from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournal,
    FilesystemAttemptJournalStore,
)
from paired_agent_evaluation.adapters.storage.filesystem import RawFilesystemStore
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.application.ports import AcceptanceRecorder
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import (
    AttemptState,
    Condition,
    ScheduledExecution,
)
from paired_agent_evaluation.domain.observations import (
    AcceptanceStatus,
    BusinessState,
    RawExecution,
)


class SequencedRunner:
    """Reject the first invocation before acceptance, then accept the retry."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution:
        del workspace
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


class InterruptedRunner:
    """Simulate interruption after durable provider acceptance."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        case: EvaluationCase,
        scheduled: ScheduledExecution,
        workspace: Path,
        *,
        acceptance: AcceptanceRecorder,
    ) -> RawExecution:
        del case, scheduled, workspace
        self.calls += 1
        acceptance.mark_accepted()
        raise KeyboardInterrupt


def _baseline_execution(answer_case: EvaluationCase) -> ScheduledExecution:
    """Return the baseline schedule entry for the shared answer case."""
    return next(
        item
        for item in build_schedule([answer_case], repetitions=1, seed=1)
        if item.key.condition == Condition.BASELINE
    )


def _build_acquisition(
    tmp_path: Path,
    runner: SequencedRunner | InterruptedRunner,
) -> AcquisitionRunner:
    """Build an acquisition runner with isolated filesystem adapters."""
    return AcquisitionRunner(
        runners={Condition.BASELINE: runner},
        store=RawFilesystemStore(tmp_path / "raw"),
        attempts=FilesystemAttemptJournalStore(tmp_path / "work"),
        max_pre_acceptance_attempts=2,
    )


def _attempt_state(tmp_path: Path, observation_id: str, attempt: int) -> AttemptState:
    """Read the durable state recorded for an acquisition attempt."""
    attempt_path = tmp_path / "work" / observation_id / f"attempt-{attempt}"
    return FilesystemAttemptJournal.load(attempt_path).record.state


def test_acquisition_retries_pre_acceptance_once_and_resumes(
    tmp_path: Path,
    answer_case: EvaluationCase,
) -> None:
    """Retry a confirmed pre-acceptance failure and skip persisted work on resume."""
    scheduled = _baseline_execution(answer_case)
    runner = SequencedRunner()
    acquisition = _build_acquisition(tmp_path, runner)

    result = acquisition.run([scheduled], [answer_case])

    assert result[0].acceptance == AcceptanceStatus.ACCEPTED
    assert runner.calls == 2
    assert (
        _attempt_state(tmp_path, scheduled.key.observation_id, 1)
        == AttemptState.PRE_ACCEPTANCE_FAILED
    )
    assert (
        _attempt_state(tmp_path, scheduled.key.observation_id, 2)
        == AttemptState.ACCEPTED_OBSERVATION_PERSISTED
    )

    acquisition.run([scheduled], [answer_case])

    assert runner.calls == 2


def test_acquisition_refuses_to_rerun_an_interrupted_accepted_attempt(
    tmp_path: Path,
    answer_case: EvaluationCase,
) -> None:
    """An accepted invocation without a raw record requires operator intervention."""
    scheduled = _baseline_execution(answer_case)
    runner = InterruptedRunner()
    acquisition = _build_acquisition(tmp_path, runner)

    with pytest.raises(KeyboardInterrupt):
        acquisition.run([scheduled], [answer_case])
    with pytest.raises(RuntimeError, match="Refusing to rerun indeterminate attempt"):
        acquisition.run([scheduled], [answer_case])

    assert runner.calls == 1
    assert _attempt_state(tmp_path, scheduled.key.observation_id, 1) == AttemptState.ACCEPTED
