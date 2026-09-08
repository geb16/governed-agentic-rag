# Fail-closed harness freezing and one-time test-split authorization.

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Protocol

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import ExperimentConfig
from paired_agent_evaluation.domain.manifests import (
    HarnessFreezeManifest,
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
    """Expose only paths needed by the experimental test-control boundary."""

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

def _run_inherited_freeze_verifiers(paths: EvaluationControlPaths) -> None:
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
    dataset = Phase5Dataset(paths.repository)
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
    """Verify inherited releases and the registered schedule before any acquisition."""

    _run_inherited_freeze_verifiers(paths)
    _verify_schedule_contract(paths)

def _source_hashes(paths: EvaluationControlPaths) -> dict[str, str]:
    return {
        path.relative_to(paths.repository).as_posix(): _sha256(path)
        for path in _source_paths(paths)
    }


def _inherited_identities(paths: EvaluationControlPaths) -> dict[str, str]:
    pass 

def _completed_validation(paths: EvaluationControlPaths, run_id: str) -> tuple[str, str]:
    pass

def write_harness_freeze(
    paths: EvaluationControlPaths,
    *,
    validation_run_id: str,
    test_run_id: str,
) -> HarnessFreezeManifest:
    """Freeze the validated harness and preregister exactly one untouched test run."""

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