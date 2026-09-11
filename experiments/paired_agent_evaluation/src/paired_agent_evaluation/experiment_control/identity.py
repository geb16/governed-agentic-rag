"""Derive source, inherited-freeze, and validation evidence identities.

References:
    [1] NIST, "FIPS 180-4: Secure Hash Standard."
        https://doi.org/10.6028/NIST.FIPS.180-4
    [2] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, TypedDict

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.domain.manifests import ExperimentManifest, HarnessFreezeManifest
from paired_agent_evaluation.experiment_control.contracts import EvaluationControlPaths


class InheritedIdentities(TypedDict):
    """Identities inherited from the Phase 3 through 5 freeze manifests."""

    phase3_freeze_id: str
    phase3_aggregate_sha256: str
    phase4_freeze_id: str
    phase4_aggregate_sha256: str
    phase5_freeze_id: str
    phase5_aggregate_sha256: str


def load_json(path: Path) -> Any:
    """Loads one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    """Returns the SHA-256 digest of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths(paths: EvaluationControlPaths) -> list[Path]:
    """Returns the sorted, deduplicated source boundary covered by the freeze."""
    fixed = [
        *(paths.project / name for name in ("README.md", "pyproject.toml", "uv.lock")),
        paths.repository / ".gitignore",
    ]
    scoped = [
        *paths.configs.glob("*.json"),
        *(paths.project / "scripts").glob("*.py"),
        *(paths.project / "src").rglob("*.py"),
        *(paths.project / "src").rglob("py.typed"),
        *(paths.project / "tests").rglob("*.py"),
        *(paths.project / "tests").rglob("*.md"),
        paths.repository / "docs" / "architecture" / "phase6_evaluation_architecture.md",
        *(paths.repository / "docs" / "phase-6-experiments").glob("*.md"),
    ]
    files = {path.resolve() for path in [*fixed, *scoped] if path.is_file()}
    return sorted(files, key=lambda path: path.as_posix())


def source_hashes(paths: EvaluationControlPaths) -> dict[str, str]:
    """Maps each frozen repository-relative source path to its digest."""
    return {
        path.relative_to(paths.repository).as_posix(): sha256_file(path)
        for path in source_paths(paths)
    }


def inherited_identities(paths: EvaluationControlPaths) -> InheritedIdentities:
    """Loads the freeze identities inherited from Phases 3 through 5."""
    phase3 = load_json(paths.repository / "docs" / "phase-3-freeze-manifest.json")
    phase4 = load_json(paths.repository / "docs" / "phase-4-freeze-manifest.json")
    phase5 = load_json(paths.repository / "docs" / "phase-5-freeze-manifest.json")
    return {
        "phase3_freeze_id": str(phase3["freeze_id"]),
        "phase3_aggregate_sha256": str(phase3["aggregate_sha256"]),
        "phase4_freeze_id": str(phase4["freeze_id"]),
        "phase4_aggregate_sha256": str(phase4["aggregate_sha256"]),
        "phase5_freeze_id": str(phase5["freeze_id"]),
        "phase5_aggregate_sha256": str(phase5["aggregate_sha256"]),
    }


def completed_validation(paths: EvaluationControlPaths, run_id: str) -> tuple[str, str]:
    """Validates final validation evidence and returns its artifact digests.

    Raises:
        ValueError: If evidence is missing, inconsistent, or incomplete.
    """
    run_root = paths.run_root(run_id)
    manifest_path = run_root / "run-manifest.json"
    summary_path = run_root / "summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        raise ValueError("Validation must have a run manifest and final summary")
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    summary = load_json(summary_path)
    if manifest.run_id != run_id or manifest.split != DatasetSplit.VALIDATION.value:
        raise ValueError("Validation evidence does not identify the requested validation run")
    if manifest.status != "scored" or not isinstance(summary, dict):
        raise ValueError("Validation run is not fully scored")
    if summary.get("run_id") != run_id or summary.get("split") != DatasetSplit.VALIDATION.value:
        raise ValueError("Validation summary identity does not match its run manifest")
    if summary.get("primary_results_final") is not True:
        raise ValueError("Validation adjudication is not final")
    observed = manifest.accepted_observations + manifest.invalid_observations
    if observed != manifest.expected_observations:
        raise ValueError("Validation observation count is incomplete")
    return sha256_file(manifest_path), sha256_file(summary_path)


def manifest_payload(manifest: HarnessFreezeManifest) -> dict[str, Any]:
    """Returns the manifest fields covered by its aggregate digest."""
    return manifest.model_dump(mode="json", exclude={"aggregate_sha256"})
