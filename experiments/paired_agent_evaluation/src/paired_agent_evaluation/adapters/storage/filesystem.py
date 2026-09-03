"""Atomic, deterministic filesystem persistence for experiment artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from paired_agent_evaluation.domain.observations import RawExecution

ModelT = TypeVar("ModelT", bound=BaseModel)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


class JsonlStore:
    @staticmethod
    def write(path: Path, models: Sequence[BaseModel]) -> None:
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
        return [model.model_validate_json(line) for line in path.read_text().splitlines() if line]
