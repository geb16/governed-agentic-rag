"""Define, sanitize, and serialize the closed release artifact set.

References:
    [1] OWASP, "Logging Cheat Sheet," Data to exclude.
        https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
    [2] Pydantic, "Serialization."
        https://docs.pydantic.dev/latest/concepts/serialization/
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json

RELEASE_FILES = (
    "run-manifest.json",
    "test-execution-claim.json",
    "schedule.json",
    "blinding-plan.json",
    "raw-results.jsonl",
    "normalized.jsonl",
    "review-packet.jsonl",
    "resolved-adjudications.jsonl",
    "secondary-ragas.jsonl",
    "scores.jsonl",
    "estimates.json",
    "paired-differences.json",
    "summary.json",
    "report.html",
)
SENSITIVE_KEY_PARTS = ("api_key", "password", "secret", "access_token", "refresh_token")


def sha256_file(path: Path) -> str:
    """Returns the SHA-256 digest of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(value: Any) -> Any:
    """Recursively redacts values whose mapping keys indicate secrets."""
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
                else sanitize(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def write_sanitized(source: Path, destination: Path) -> None:
    """Copies HTML or writes sanitized, deterministic JSON content."""
    write_payload(destination, read_payload(source))


def write_payload(destination: Path, value: Any) -> None:
    """Writes one sanitized release payload using its canonical file encoding."""
    value = sanitize(json_value(value))
    if destination.suffix == ".html":
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(str(value), encoding="utf-8", newline="\n")
        return
    if destination.suffix == ".jsonl":
        destination.parent.mkdir(parents=True, exist_ok=True)
        records = value if isinstance(value, list) else [value]
        content = "".join(
            json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
            for record in records
        )
        destination.write_text(content, encoding="utf-8", newline="\n")
        return
    atomic_json(destination, value)


def read_payload(path: Path) -> Any:
    """Reads an HTML, JSON Lines, or JSON artifact for comparison."""
    if path.suffix == ".html":
        return path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return json.loads(path.read_text(encoding="utf-8"))


def json_value(value: Any) -> Any:
    """Converts Pydantic models and model lists to JSON-compatible values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [json_value(item) for item in value]
    return value
