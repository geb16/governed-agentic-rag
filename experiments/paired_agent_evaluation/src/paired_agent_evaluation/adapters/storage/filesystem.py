"""Provides deterministic filesystem persistence for experiment artifacts.

JSON values use a stable encoding when hashed, while artifact writers use
same-directory replacement to avoid exposing partially written destination
files. Control records can instead require exclusive creation. JSON Lines
stores preserve model order and validate records when loading them.

References:
    [1] NIST, "Secure Hash Standard (SHS)," FIPS 180-4.
        https://doi.org/10.6028/NIST.FIPS.180-4
    [2] JSON Lines, "JSON Lines Documentation."
        https://jsonlines.org/
    [3] SLSA, "Build: Provenance," v1.0.
        https://slsa.dev/spec/v1.0/provenance
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from paired_agent_evaluation.domain.observations import RawExecution

ModelT = TypeVar("ModelT", bound=BaseModel)


def directory_has_payload(path: Path, *, ignored_names: frozenset[str]) -> bool:
    """Return whether a directory contains an entry other than named placeholders."""
    return path.exists() and any(item.name not in ignored_names for item in path.iterdir())


def canonical_json(value: Any) -> bytes:
    """Serializes a JSON-compatible value into stable bytes.

    Object keys are sorted, insignificant whitespace is removed, and non-ASCII
    characters are escaped so logically equivalent inputs produce the same
    representation regardless of insertion order.

    Args:
        value: JSON-compatible value to serialize.

    Returns:
        Deterministically encoded ASCII-safe JSON bytes.

    Raises:
        TypeError: If ``value`` contains an unsupported object or key type.
        ValueError: If circular references prevent serialization.
    """
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()


def sha256_json(value: Any) -> str:
    """Computes the SHA-256 digest of a canonical JSON representation.

    Args:
        value: JSON-compatible value whose logical content identifies an artifact.

    Returns:
        A lowercase hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(canonical_json(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    """Writes formatted JSON through same-directory file replacement.

    The complete payload is written to a sibling ``.tmp`` path before replacing
    the destination, preventing readers from observing a partially written
    destination file. This function does not provide cross-process locking.

    Args:
        path: Destination artifact path.
        value: JSON-compatible value to persist.

    Raises:
        OSError: If the directory, temporary file, or replacement cannot be written.
        TypeError: If ``value`` is not JSON serializable.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def exclusive_json(path: Path, value: Any) -> None:
    """Creates a JSON control record only when no prior record exists.

    Args:
        path: New control-record path.
        value: JSON-compatible value to persist.

    Raises:
        FileExistsError: If ``path`` already exists.
        OSError: If the parent directory or record cannot be written.
        TypeError: If ``value`` is not JSON serializable.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


class RawFilesystemStore:
    """Stores one validated raw execution per observation.

    Args:
        root: Directory containing observation JSON files.

    Attributes:
        root: Configured observation directory, created during initialization.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, observation_id: str) -> Path:
        """Returns the JSON artifact path for an observation identity."""
        return self.root / f"{observation_id}.json"

    def exists(self, observation_id: str) -> bool:
        """Reports whether an observation has a persisted regular file."""
        return self._path(observation_id).is_file()

    def write(self, execution: RawExecution) -> Path:
        """Serializes an execution to its observation artifact.

        Args:
            execution: Validated raw execution to persist.

        Returns:
            Path of the written JSON artifact.
        """
        path = self._path(execution.key.observation_id)
        atomic_json(path, execution.model_dump(mode="json"))
        return path

    def read_all(self) -> list[RawExecution]:
        """Loads all observation artifacts in filename order.

        Returns:
            Strictly validated raw executions ordered by artifact filename.

        Raises:
            OSError: If an artifact cannot be read.
            ValueError: If an artifact violates the raw-execution schema.
        """
        return [
            RawExecution.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*.json"))
        ]


class JsonlStore:
    """Reads and writes ordered collections of validated models as JSON Lines."""

    @staticmethod
    def write(path: Path, models: Sequence[BaseModel]) -> None:
        """Writes models as compact, deterministically keyed JSON Lines.

        Args:
            path: Destination JSONL artifact.
            models: Ordered models to serialize, one per line.

        Raises:
            OSError: If the temporary file or destination cannot be written.
            TypeError: If a model contains a value that cannot be serialized.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        content = "".join(
            json.dumps(item.model_dump(mode="json"), separators=(",", ":"), sort_keys=True) + "\n"
            for item in models
        )
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.replace(path)

    @staticmethod
    def read(path: Path, model: type[ModelT]) -> list[ModelT]:
        """Loads nonempty JSON Lines through a model contract.

        Args:
            path: UTF-8 JSONL artifact to read.
            model: Model class used to validate each record.

        Returns:
            Validated models in file order.

        Raises:
            OSError: If the artifact cannot be read.
            ValueError: If a line is malformed or violates the model schema.
        """
        return [model.model_validate_json(line) for line in path.read_text().splitlines() if line]
