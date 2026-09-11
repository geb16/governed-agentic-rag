"""Seal a completed test run into a sanitized, content-addressed release.

References:
    [1] OWASP, "Logging Cheat Sheet," Data to exclude.
        https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
    [2] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json, canonical_json
from paired_agent_evaluation.domain.manifests import (
    ExperimentManifest,
    ReleaseManifest,
    TestExecutionClaim,
)
from paired_agent_evaluation.release.artifacts import (
    RELEASE_FILES,
    sha256_file,
    write_sanitized,
)
from paired_agent_evaluation.release.verification import verify_primary_artifacts


def seal_run(*, run_root: Path, release_root: Path) -> ReleaseManifest:
    """Seals one final test run into an empty release directory.

    The run must be scored, adjudicated, claimed for testing, and independently
    reproducible. Sanitized artifacts are bound to per-file and aggregate digests.

    Returns:
        The persisted content-addressed release manifest.

    Raises:
        ValueError: If prerequisites, verification, or destination checks fail.
        OSError: If release artifacts cannot be read or written.
    """
    missing = [name for name in RELEASE_FILES if not (run_root / name).is_file()]
    if missing:
        raise ValueError(f"Cannot seal incomplete run; missing: {', '.join(missing)}")
    run_manifest = ExperimentManifest.model_validate_json(
        (run_root / "run-manifest.json").read_text(encoding="utf-8")
    )
    summary: dict[str, Any] = json.loads((run_root / "summary.json").read_text(encoding="utf-8"))
    if run_manifest.status != "scored" or not summary.get("primary_results_final"):
        raise ValueError("Only a fully adjudicated scored run can be sealed")
    if run_manifest.split != "test":
        raise ValueError(
            f"Only a test-split run can be sealed; refusing split={run_manifest.split!r}"
        )
    claim = TestExecutionClaim.model_validate_json(
        (run_root / "test-execution-claim.json").read_text(encoding="utf-8")
    )
    if claim.test_run_id != run_manifest.run_id:
        raise ValueError("Test execution claim does not match the sealed run")
    verify_primary_artifacts(run_root, run_manifest)
    if release_root.exists() and any(release_root.iterdir()):
        raise ValueError("Release directory must be empty before sealing")
    release_root.mkdir(parents=True, exist_ok=True)
    for name in RELEASE_FILES:
        write_sanitized(run_root / name, release_root / name)
    hashes = {name: sha256_file(release_root / name) for name in RELEASE_FILES}
    payload = {
        "release_id": "paired-agent-evaluation-v1",
        "run_id": run_manifest.run_id,
        "source_run_manifest_sha256": sha256_file(run_root / "run-manifest.json"),
        "files": hashes,
    }
    manifest = ReleaseManifest(
        **payload,
        aggregate_sha256=hashlib.sha256(canonical_json(payload)).hexdigest(),
        sealed_at=datetime.now(UTC),
    )
    atomic_json(release_root / "manifest.json", manifest.model_dump(mode="json"))
    return manifest
