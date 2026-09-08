# Phase 6 sanitization and content-addressed release sealing.

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json, canonical_json
from paired_agent_evaluation.domain.manifests import ReleaseManifest

RELEASE_FILES = (
    "run-manifest.json",
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
)
SENSITIVE_KEY_PARTS = ("api_key", "password", "secret", "access_token", "refresh_token")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
                else _sanitize(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _write_sanitized(source: Path, destination: Path) -> None:
    if source.suffix == ".jsonl":
        records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
        content = "".join(
            json.dumps(_sanitize(record), separators=(",", ":"), sort_keys=True) + "\n"
            for record in records
        )
        destination.write_text(content, encoding="utf-8", newline="\n")
        return
    atomic_json(destination, _sanitize(json.loads(source.read_text(encoding="utf-8"))))


def seal_run(*, run_root: Path, release_root: Path) -> ReleaseManifest:
    missing = [name for name in RELEASE_FILES if not (run_root / name).is_file()]
    if missing:
        raise ValueError(f"Cannot seal incomplete run; missing: {', '.join(missing)}")
    run_manifest: dict[str, Any] = json.loads(
        (run_root / "run-manifest.json").read_text(encoding="utf-8")
    )
    summary: dict[str, Any] = json.loads((run_root / "summary.json").read_text(encoding="utf-8"))
    if run_manifest.get("status") != "scored" or not summary.get("primary_results_final"):
        raise ValueError("Only a fully adjudicated scored run can be sealed")
    if run_manifest.get("split") != "test":
        raise ValueError(
            f"Only a test-split run can be sealed; refusing split={run_manifest.get('split')!r}"
        )
    if release_root.exists() and any(release_root.iterdir()):
        raise ValueError("Release directory must be empty before sealing")
    release_root.mkdir(parents=True, exist_ok=True)
    for name in RELEASE_FILES:
        _write_sanitized(run_root / name, release_root / name)
    hashes = {name: _sha256(release_root / name) for name in RELEASE_FILES}
    payload = {
        "release_id": "paired-agent-evaluation-v1",
        "run_id": str(run_manifest["run_id"]),
        "source_run_manifest_sha256": _sha256(run_root / "run-manifest.json"),
        "files": hashes,
    }
    manifest = ReleaseManifest(
        **payload,
        aggregate_sha256=hashlib.sha256(canonical_json(payload)).hexdigest(),
        sealed_at=datetime.now(UTC),
    )
    atomic_json(release_root / "manifest.json", manifest.model_dump(mode="json"))
    return manifest


def verify_release(release_root: Path) -> ReleaseManifest:
    manifest = ReleaseManifest.model_validate_json(
        (release_root / "manifest.json").read_text(encoding="utf-8")
    )
    actual = {path.name for path in release_root.iterdir() if path.is_file()}
    if actual != {*manifest.files, "manifest.json"}:
        raise ValueError("Release file set is not closed")
    for name, digest in manifest.files.items():
        if _sha256(release_root / name) != digest:
            raise ValueError(f"Release hash mismatch: {name}")
    payload = {
        "release_id": manifest.release_id,
        "run_id": manifest.run_id,
        "source_run_manifest_sha256": manifest.source_run_manifest_sha256,
        "files": manifest.files,
    }
    if hashlib.sha256(canonical_json(payload)).hexdigest() != manifest.aggregate_sha256:
        raise ValueError("Release aggregate mismatch")
    return manifest
