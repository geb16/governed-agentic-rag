"""Freeze the evaluation harness and gate one preregistered test execution.

The control boundary verifies inherited freezes, binds validation evidence and
source files to digests, and atomically consumes authorization before test access.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.1 and 2.13.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
    [2] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
    [3] NIST, "FIPS 180-4: Secure Hash Standard."
        https://doi.org/10.6028/NIST.FIPS.180-4
    [4] Python Software Foundation, "subprocess — Subprocess management."
        https://docs.python.org/3/library/subprocess.html
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.storage.filesystem import (
    atomic_json,
    exclusive_json,
    sha256_json,
)
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import ExperimentConfig
from paired_agent_evaluation.domain.manifests import (
    ExperimentManifest,
    HarnessFreezeManifest,
    TestExecutionClaim,
)

HARNESS_FREEZE_ID = "paired-agent-evaluation-harness-v1"
HARNESS_MANIFEST = Path("docs/phase-6-experiments/harness-freeze-manifest.json")
TEST_EXECUTION_CLAIM = Path("data/evaluation/paired_agent_evaluation/test-execution-claim.json")
INHERITED_VERIFIERS = (
    "scripts/verify_phase3_freeze.py",
    "scripts/verify_phase4_freeze.py",
    "scripts/verify_phase5_freeze.py",
)


class EvaluationControlPaths(Protocol):
    """Exposes only paths required by the experiment-control boundary."""

    @property
    def repository(self) -> Path: ...

    @property
    def project(self) -> Path: ...

    @property
    def artifacts(self) -> Path: ...

    @property
    def release(self) -> Path: ...

    @property
    def configs(self) -> Path: ...

    def run_root(self, run_id: str) -> Path: ...


def _json(path: Path) -> Any:
    """Loads one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    """Returns the SHA-256 digest of a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_inherited_freeze_verifiers(paths: EvaluationControlPaths) -> None:
    """Runs every inherited phase verifier and reports all failures together."""
    failed: list[str] = []
    for script in INHERITED_VERIFIERS:
        result = subprocess.run(
            [sys.executable, script],
            cwd=paths.repository,
            check=False,
            text=True,
        )
        if result.returncode:
            failed.append(script)
    if failed:
        raise ValueError(f"Inherited freeze verification failed: {', '.join(failed)}")


def _verify_schedule_contract(paths: EvaluationControlPaths) -> None:
    """Validates the frozen observation count for each controlled split."""
    dataset = EvaluationDataset(paths.repository)
    config = ExperimentConfig.model_validate(_json(paths.configs / "experiment.json"))
    expected = {DatasetSplit.VALIDATION: 120, DatasetSplit.TEST: 480}
    for split, count in expected.items():
        schedule = build_schedule(
            dataset.cases(split),
            repetitions=config.repetitions_per_case,
            seed=config.condition_order_seed,
        )
        if len(schedule) != count:
            raise ValueError(
                f"{split.value} schedule has {len(schedule)} entries; expected {count}"
            )


def verify_harness_readiness(paths: EvaluationControlPaths) -> None:
    """Verifies inherited freezes and schedule cardinality before acquisition."""

    _run_inherited_freeze_verifiers(paths)
    _verify_schedule_contract(paths)


def _source_paths(paths: EvaluationControlPaths) -> list[Path]:
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


def _source_hashes(paths: EvaluationControlPaths) -> dict[str, str]:
    """Maps each frozen repository-relative source path to its digest."""
    return {
        path.relative_to(paths.repository).as_posix(): _sha256(path)
        for path in _source_paths(paths)
    }


def _inherited_identities(paths: EvaluationControlPaths) -> dict[str, str]:
    """Loads the freeze identities inherited from Phases 3 through 5."""
    phase3 = _json(paths.repository / "docs" / "phase-3-freeze-manifest.json")
    phase4 = _json(paths.repository / "docs" / "phase-4-freeze-manifest.json")
    phase5 = _json(paths.repository / "docs" / "phase-5-freeze-manifest.json")
    return {
        "phase3_freeze_id": str(phase3["freeze_id"]),
        "phase3_aggregate_sha256": str(phase3["aggregate_sha256"]),
        "phase4_freeze_id": str(phase4["freeze_id"]),
        "phase4_aggregate_sha256": str(phase4["aggregate_sha256"]),
        "phase5_freeze_id": str(phase5["freeze_id"]),
        "phase5_aggregate_sha256": str(phase5["aggregate_sha256"]),
    }


def _completed_validation(paths: EvaluationControlPaths, run_id: str) -> tuple[str, str]:
    """Validates final validation evidence and returns its artifact digests.

    Raises:
        ValueError: If evidence is missing, inconsistent, unfinished, or incomplete.
    """
    run_root = paths.run_root(run_id)
    manifest_path = run_root / "run-manifest.json"
    summary_path = run_root / "summary.json"
    if not manifest_path.is_file() or not summary_path.is_file():
        raise ValueError("Validation must have a run manifest and final summary")
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    summary = _json(summary_path)
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
    return _sha256(manifest_path), _sha256(summary_path)


def _manifest_payload(manifest: HarnessFreezeManifest) -> dict[str, Any]:
    """Returns the manifest fields covered by its aggregate digest."""
    return manifest.model_dump(mode="json", exclude={"aggregate_sha256"})


def write_harness_freeze(
    paths: EvaluationControlPaths,
    *,
    validation_run_id: str,
    test_run_id: str,
) -> HarnessFreezeManifest:
    """Freezes a validated harness and preregisters one untouched test run.

    The operation is refused after any test claim, test run directory, or sealed
    release exists. It verifies inherited artifacts and completed validation before
    hashing the controlled source boundary and writing the aggregate manifest.

    Args:
        paths: Controlled repository and artifact locations.
        validation_run_id: Completed validation run that justifies the freeze.
        test_run_id: Distinct run identity authorized for the test split.

    Returns:
        The persisted, self-digested harness freeze manifest.

    Raises:
        ValueError: If prerequisites, identities, or lifecycle guards fail.
        OSError: If required evidence cannot be read or the manifest cannot be written.
    """

    if validation_run_id == test_run_id:
        raise ValueError("Validation and test runs require distinct identifiers")
    if (paths.repository / TEST_EXECUTION_CLAIM).exists():
        raise ValueError("Test execution has already been claimed; harness cannot be refrozen")
    if paths.run_root(test_run_id).exists():
        raise ValueError("Preregistered test run directory already exists")
    if paths.release.exists() and any(paths.release.iterdir()):
        raise ValueError("A sealed test release already exists")
    verify_harness_readiness(paths)
    validation_manifest_hash, validation_summary_hash = _completed_validation(
        paths, validation_run_id
    )
    manifest = HarnessFreezeManifest(
        freeze_id=HARNESS_FREEZE_ID,
        preregistered_test_run_id=test_run_id,
        validation_run_id=validation_run_id,
        validation_run_manifest_sha256=validation_manifest_hash,
        validation_summary_sha256=validation_summary_hash,
        source_files=_source_hashes(paths),
        aggregate_sha256="0" * 64,
        **_inherited_identities(paths),
    )
    manifest = manifest.model_copy(
        update={"aggregate_sha256": sha256_json(_manifest_payload(manifest))}
    )
    atomic_json(
        paths.repository / HARNESS_MANIFEST,
        manifest.model_dump(mode="json"),
    )
    return manifest


def verify_harness_freeze(paths: EvaluationControlPaths) -> HarnessFreezeManifest:
    """Verifies the harness manifest and every identity bound by its freeze.

    Returns:
        The validated manifest when source, inherited, validation, and aggregate
        digests all match.

    Raises:
        ValueError: If the harness is unfrozen or any frozen identity has drifted.
    """

    verify_harness_readiness(paths)
    manifest_path = paths.repository / HARNESS_MANIFEST
    if not manifest_path.is_file():
        raise ValueError("Phase 6 harness is not frozen and preregistered")
    manifest = HarnessFreezeManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.freeze_id != HARNESS_FREEZE_ID:
        raise ValueError("Unexpected Phase 6 harness freeze identity")
    if manifest.source_files != _source_hashes(paths):
        raise ValueError("Phase 6 harness source files changed after preregistration")
    inherited = _inherited_identities(paths)
    if any(getattr(manifest, name) != value for name, value in inherited.items()):
        raise ValueError("Inherited freeze identity changed after Phase 6 preregistration")
    validation_manifest_hash, validation_summary_hash = _completed_validation(
        paths, manifest.validation_run_id
    )
    if (
        validation_manifest_hash != manifest.validation_run_manifest_sha256
        or validation_summary_hash != manifest.validation_summary_sha256
    ):
        raise ValueError("Validation evidence changed after Phase 6 preregistration")
    if sha256_json(_manifest_payload(manifest)) != manifest.aggregate_sha256:
        raise ValueError("Phase 6 harness aggregate hash mismatch")
    return manifest


def _existing_test_runs(paths: EvaluationControlPaths) -> list[str]:
    """Returns sorted test-run identities already present in artifact manifests."""
    runs: list[str] = []
    if not paths.artifacts.exists():
        return runs
    for manifest_path in paths.artifacts.glob("run_*/run-manifest.json"):
        manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if manifest.split == DatasetSplit.TEST.value:
            runs.append(manifest.run_id)
    return sorted(runs)


def claim_test_execution(
    paths: EvaluationControlPaths,
    *,
    run_id: str,
) -> TestExecutionClaim:
    """Atomically consumes authorization for the preregistered test run.

    The claim is created exclusively only after verifying the frozen harness, exact
    run identity, and absence of prior test artifacts or a sealed release. A
    concurrent or repeated claimant therefore fails before provider access.

    Args:
        paths: Controlled repository and artifact locations.
        run_id: Test identity recorded in the harness freeze.

    Returns:
        The persisted claim binding the test run to its harness and validation run.

    Raises:
        ValueError: If the harness changed, the identity differs, test execution
            already occurred, or authorization was previously consumed.
        OSError: If control artifacts cannot be read or the claim cannot be written.
    """

    manifest = verify_harness_freeze(paths)
    if run_id != manifest.preregistered_test_run_id:
        raise ValueError("Test run ID does not match the preregistered harness identity")
    prior_runs = _existing_test_runs(paths)
    if prior_runs:
        raise ValueError(f"Test split was already executed: {', '.join(prior_runs)}")
    if paths.run_root(run_id).exists():
        raise ValueError("Preregistered test run directory already exists")
    if paths.release.exists() and any(paths.release.iterdir()):
        raise ValueError("A sealed test release already exists")
    claim = TestExecutionClaim(
        test_run_id=run_id,
        harness_freeze_id=manifest.freeze_id,
        harness_aggregate_sha256=manifest.aggregate_sha256,
        validation_run_id=manifest.validation_run_id,
    )
    claim_path = paths.repository / TEST_EXECUTION_CLAIM
    try:
        exclusive_json(claim_path, claim.model_dump(mode="json"))
    except FileExistsError as error:
        raise ValueError("Test execution authorization has already been consumed") from error
    return claim
