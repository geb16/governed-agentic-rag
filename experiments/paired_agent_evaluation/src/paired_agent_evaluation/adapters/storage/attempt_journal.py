# Atomic filesystem journal for fail-closed acquisition retries.

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json, exclusive_json
from paired_agent_evaluation.domain.executions import AttemptRecord, AttemptState


class FilesystemAttemptJournal:
    """Advance one attempt through durable, monotonic acceptance states."""

    _FILENAME = "attempt.json"

    def __init__(self, path: Path, record: AttemptRecord) -> None:
        self._path = path
        self._record = record

    @classmethod
    def begin(cls, root: Path, *, observation_id: str, attempt: int) -> FilesystemAttemptJournal:
        """Create a started record before any system or provider invocation."""
        root.mkdir(parents=True, exist_ok=False)
        record = AttemptRecord(
            observation_id=observation_id,
            attempt=attempt,
            state=AttemptState.STARTED,
        )
        path = root / cls._FILENAME
        exclusive_json(path, record.model_dump(mode="json"))
        return cls(path, record)

    @classmethod
    def load(cls, root: Path) -> FilesystemAttemptJournal:
        """Load and validate an existing attempt record."""
        path = root / cls._FILENAME
        if not path.is_file():
            raise RuntimeError(f"Attempt journal is missing: {path}")
        return cls(path, AttemptRecord.model_validate_json(path.read_text(encoding="utf-8")))

    @property
    def record(self) -> AttemptRecord:
        return self._record

    @property
    def workspace(self) -> Path:
        return self._path.parent

    @property
    def accepted(self) -> bool:
        return self._record.state in {
            AttemptState.ACCEPTED,
            AttemptState.ACCEPTED_OBSERVATION_PERSISTED,
        }

    def mark_accepted(self) -> None:
        """Persist the first evidence that an invocation must not be retried."""
        if self._record.state == AttemptState.ACCEPTED:
            return
        if self._record.state != AttemptState.STARTED:
            raise RuntimeError(f"Cannot accept attempt in state {self._record.state.value}")
        self._replace(state=AttemptState.ACCEPTED)

    def mark_pre_acceptance_failed(self, error_type: str | None) -> None:
        """Record a proven pre-acceptance failure that may be retried."""
        if self._record.state != AttemptState.STARTED:
            raise RuntimeError(
                f"Cannot record pre-acceptance failure in state {self._record.state.value}"
            )
        self._replace(state=AttemptState.PRE_ACCEPTANCE_FAILED, error_type=error_type)

    def mark_observation_persisted(self) -> None:
        """Close the attempt only after its raw observation is durable."""
        if self._record.state not in {
            AttemptState.ACCEPTED,
            AttemptState.PRE_ACCEPTANCE_FAILED,
        }:
            raise RuntimeError(f"Cannot close attempt in state {self._record.state.value}")
        state = (
            AttemptState.ACCEPTED_OBSERVATION_PERSISTED
            if self._record.state == AttemptState.ACCEPTED
            else AttemptState.INVALID_OBSERVATION_PERSISTED
        )
        self._replace(state=state)

    def _replace(self, *, state: AttemptState, error_type: str | None = None) -> None:
        self._record = self._record.model_copy(
            update={
                "state": state,
                "updated_at": datetime.now(UTC),
                "error_type": error_type,
            }
        )
        atomic_json(self._path, self._record.model_dump(mode="json"))


class FilesystemAttemptJournalStore:
    """Store isolated attempt journals beneath one acquisition workspace."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def list(self, observation_id: str) -> list[FilesystemAttemptJournal]:
        roots = sorted((self._root / observation_id).glob("attempt-*"))
        return [FilesystemAttemptJournal.load(root) for root in roots]

    def begin(self, observation_id: str, attempt: int) -> FilesystemAttemptJournal:
        return FilesystemAttemptJournal.begin(
            self._root / observation_id / f"attempt-{attempt}",
            observation_id=observation_id,
            attempt=attempt,
        )
