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
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

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
