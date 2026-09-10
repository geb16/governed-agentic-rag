"""Persists fail-closed state transitions for acquisition attempts.

Each attempt owns an exclusive directory and a validated ``attempt.json``
record. State changes are written through atomic replacement so interrupted or
indeterminate attempts cannot be silently retried as known pre-acceptance
failures.

References:
    [1] Pydantic, "Models."
        https://docs.pydantic.dev/latest/concepts/models/
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json, exclusive_json
from paired_agent_evaluation.domain.executions import AttemptRecord, AttemptState


class FilesystemAttemptJournal:
    """Controls monotonic state transitions for one acquisition attempt.

    A new journal starts in ``started`` and may record either request acceptance
    or a confirmed pre-acceptance failure. Once the resulting observation is
    stored, the journal moves to the corresponding terminal state. Invalid or
    ambiguous transitions fail closed with ``RuntimeError``.
    """

    _FILENAME = "attempt.json"

    def __init__(self, path: Path, record: AttemptRecord) -> None:
        self._path = path
        self._record = record

    @classmethod
    def begin(cls, root: Path, *, observation_id: str, attempt: int) -> FilesystemAttemptJournal:
        """Creates a journal before invoking a system or provider.

        Args:
            root: New directory dedicated to this attempt.
            observation_id: Stable identity of the scheduled observation.
            attempt: One-based attempt number.

        Returns:
            A journal whose state is ``started``.

        Raises:
            FileExistsError: If the attempt directory already exists.
            OSError: If the directory or initial record cannot be written.
            ValueError: If the attempt data violates its domain contract.
        """
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
        """Loads and validates an existing attempt journal.

        Args:
            root: Attempt directory containing ``attempt.json``.

        Returns:
            A journal restored to its persisted state.

        Raises:
            RuntimeError: If the journal file is missing.
            OSError: If the journal file cannot be read.
            ValueError: If its JSON does not satisfy the attempt schema.
        """
        path = root / cls._FILENAME
        if not path.is_file():
            raise RuntimeError(f"Attempt journal is missing: {path}")
        return cls(path, AttemptRecord.model_validate_json(path.read_text(encoding="utf-8")))

    @property
    def record(self) -> AttemptRecord:
        """Returns the journal's current validated record."""
        return self._record

    @property
    def workspace(self) -> Path:
        """Returns the attempt directory for invocation-specific artifacts."""
        return self._path.parent

    @property
    def accepted(self) -> bool:
        """Reports whether request acceptance has been recorded."""
        return self._record.state in {
            AttemptState.ACCEPTED,
            AttemptState.ACCEPTED_OBSERVATION_PERSISTED,
        }

    def mark_accepted(self) -> None:
        """Records evidence that the provider accepted the request.

        Repeating this transition while already accepted is idempotent. An
        accepted request must not be invoked again, even if its observation has
        not yet been persisted.

        Raises:
            RuntimeError: If the journal is neither ``started`` nor already accepted.
            OSError: If the updated record cannot be written.
        """
        if self._record.state == AttemptState.ACCEPTED:
            return
        if self._record.state != AttemptState.STARTED:
            raise RuntimeError(f"Cannot accept attempt in state {self._record.state.value}")
        self._replace(state=AttemptState.ACCEPTED)

    def mark_pre_acceptance_failed(self, error_type: str | None) -> None:
        """Records a confirmed failure before provider acceptance.

        Args:
            error_type: Stable failure classification, if one is available.

        Raises:
            RuntimeError: If the journal is not in the ``started`` state.
            OSError: If the updated record cannot be written.
        """
        if self._record.state != AttemptState.STARTED:
            raise RuntimeError(
                f"Cannot record pre-acceptance failure in state {self._record.state.value}"
            )
        self._replace(state=AttemptState.PRE_ACCEPTANCE_FAILED, error_type=error_type)

    def mark_observation_persisted(self) -> None:
        """Closes the attempt after its raw observation has been stored.

        Accepted attempts become ``accepted_observation_persisted``; confirmed
        pre-acceptance failures become ``invalid_observation_persisted``.

        Raises:
            RuntimeError: If acceptance or pre-acceptance failure is unrecorded.
            OSError: If the terminal record cannot be written.
        """
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
        """Replaces the current record with an updated timestamp and state."""
        self._record = self._record.model_copy(
            update={
                "state": state,
                "updated_at": datetime.now(UTC),
                "error_type": error_type,
            }
        )
        atomic_json(self._path, self._record.model_dump(mode="json"))


class FilesystemAttemptJournalStore:
    """Organizes attempt journals beneath an acquisition workspace.

    Args:
        root: Directory containing one subdirectory per observation and attempt.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def list(self, observation_id: str) -> list[FilesystemAttemptJournal]:
        """Loads an observation's attempt journals in lexical attempt order.

        Args:
            observation_id: Stable identity of the scheduled observation.

        Returns:
            Validated journals found below the observation directory.
        """
        roots = sorted((self._root / observation_id).glob("attempt-*"))
        return [FilesystemAttemptJournal.load(root) for root in roots]

    def begin(self, observation_id: str, attempt: int) -> FilesystemAttemptJournal:
        """Creates the numbered journal for an observation attempt.

        Args:
            observation_id: Stable identity of the scheduled observation.
            attempt: One-based attempt number.

        Returns:
            A new journal in the ``started`` state.
        """
        return FilesystemAttemptJournal.begin(
            self._root / observation_id / f"attempt-{attempt}",
            observation_id=observation_id,
            attempt=attempt,
        )
