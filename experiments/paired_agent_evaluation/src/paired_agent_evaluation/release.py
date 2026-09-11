"""Sanitize, seal, and verify the final evaluation release.

Sealing independently re-derives primary results, removes named secret fields, and
binds a closed artifact set to per-file and aggregate SHA-256 digests.

References:
    [1] OWASP, "Logging Cheat Sheet," Data to exclude.
        https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
    [2] Pydantic, "Configuration." 
        https://pydantic.dev/docs/validation/latest/api/pydantic/base_model/
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from paired_agent_evaluation.adapters.storage.filesystem import atomic_json, canonical_json
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.manifests import (
    ExperimentManifest,
    ReleaseManifest,
    TestExecutionClaim,
)
from paired_agent_evaluation.reporting import derive_primary_artifacts
from paired_agent_evaluation.visual_report import render_html_report

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


def _sha256(path: Path) -> str:
    """Returns the SHA-256 digest of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sanitize(value: Any) -> Any:
    """Recursively redacts values whose mapping keys indicate secrets."""
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
    """Copies HTML or writes sanitized, deterministic JSON content."""
    if source.suffix == ".html":
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
        return
    if source.suffix == ".jsonl":
        records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
        content = "".join(
            json.dumps(_sanitize(record), separators=(",", ":"), sort_keys=True) + "\n"
            for record in records
        )
        destination.write_text(content, encoding="utf-8", newline="\n")
        return
    atomic_json(destination, _sanitize(json.loads(source.read_text(encoding="utf-8"))))


def _read_payload(path: Path) -> Any:
    """Reads an HTML, JSON Lines, or JSON artifact for semantic comparison."""
    if path.suffix == ".html":
        return path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return json.loads(path.read_text(encoding="utf-8"))


def _json_value(value: Any) -> Any:
    """Converts models and model lists to JSON-compatible values."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def verify_primary_artifacts(run_root: Path, manifest: ExperimentManifest) -> None:
    """Verifies stored primary results against an independent derivation.

    Structured artifacts are compared semantically. The HTML report is regenerated
    from the independently derived summary, estimates, and paired differences and
    then compared byte-for-text with the stored report.

    Args:
        run_root: Scored run containing the primary artifacts.
        manifest: Validated manifest governing the derivation.

    Raises:
        ValueError: If any stored primary artifact differs from its derivation.
        OSError: If a required artifact cannot be read.
    """

    expected = derive_primary_artifacts(
        paths=EvaluationPaths.discover(), run_root=run_root, manifest=manifest
    )
    drift = [
        name
        for name, payload in expected.items()
        if _read_payload(run_root / name) != _json_value(payload)
    ]
    report_inputs = {"summary.json", "estimates.json", "paired-differences.json"}
    if report_inputs <= expected.keys():
        expected_report = render_html_report(
            expected["summary.json"],
            expected["estimates.json"],
            expected["paired-differences.json"],
        )
        if _read_payload(run_root / "report.html") != expected_report:
            drift.append("report.html")
    if drift:
        raise ValueError(f"Primary derived artifacts have changed: {', '.join(drift)}")


def seal_run(*, run_root: Path, release_root: Path) -> ReleaseManifest:
    """Seals one final test run into an empty release directory.

    The run must be fully scored and adjudicated, belong to the test split, carry
    its matching execution claim, and reproduce every primary artifact. JSON
    artifacts are sanitized before per-file hashes and the closed file-set digest
    are recorded in the release manifest.

    Args:
        run_root: Source directory containing the complete scored run.
        release_root: Empty destination for sanitized release artifacts.

    Returns:
        The persisted content-addressed release manifest.

    Raises:
        ValueError: If the run is incomplete, non-final, not a claimed test run,
            fails deterministic verification, or the destination is not empty.
        OSError: If source artifacts cannot be read or release files cannot be written.
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
        _write_sanitized(run_root / name, release_root / name)
    hashes = {name: _sha256(release_root / name) for name in RELEASE_FILES}
    payload = {
        "release_id": "paired-agent-evaluation-v1",
        "run_id": run_manifest.run_id,
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
    """Verifies the closed file set and all release content digests.

    Args:
        release_root: Directory containing a sealed release and its manifest.

    Returns:
        The validated release manifest.

    Raises:
        ValueError: If the file set, a file digest, or the aggregate digest differs.
        OSError: If the release directory or one of its files cannot be read.
    """

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
