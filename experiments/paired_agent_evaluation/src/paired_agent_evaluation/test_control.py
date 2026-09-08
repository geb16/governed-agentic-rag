# Fail-closed harness freezing and one-time test-split authorization.

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from paired_agent_evaluation.domain.manifests import HarnessFreezeManifest

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
