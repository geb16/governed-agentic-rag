"""Read, verify, and write deterministic Phase 7 evidence files."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence_config import RELEASE_ID, RELEASE_SHA256

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ReleaseData:
    """In-memory inputs loaded from a verified Phase 6 release."""

    manifest: JsonObject
    estimates: list[JsonObject]
    differences: list[JsonObject]
    summary: JsonObject
    normalized: list[JsonObject]
    scores: list[JsonObject]
    ragas: list[JsonObject]


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_release(release: Path) -> ReleaseData:
    """Verify the sealed release and load every analysis input."""

    manifest = _load_json(release / "manifest.json")
    _verify_manifest(release, manifest)
    return ReleaseData(
        manifest=manifest,
        estimates=_load_json(release / "estimates.json"),
        differences=_load_json(release / "paired-differences.json"),
        summary=_load_json(release / "summary.json"),
        normalized=_load_jsonl(release / "normalized.jsonl"),
        scores=_load_jsonl(release / "scores.jsonl"),
        ragas=_load_jsonl(release / "secondary-ragas.jsonl"),
    )


def write_csv(path: Path, headings: list[str], rows: list[list[Any]]) -> None:
    """Write a CSV with stable newlines and column order."""

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headings)
        writer.writerows(rows)

def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _load_jsonl(path: Path) -> list[JsonObject]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _verify_manifest(release: Path, manifest: JsonObject) -> None:
    if manifest["release_id"] != RELEASE_ID or manifest["aggregate_sha256"] != RELEASE_SHA256:
        raise ValueError("The source is not the approved sealed Phase 6 release")
    for relative, expected in manifest["files"].items():
        actual = sha256(release / relative)
        if actual != expected:
            raise ValueError(f"Sealed source digest mismatch: {relative}")
