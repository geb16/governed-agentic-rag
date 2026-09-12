"""Verify harness freezing and one-time authorization of test execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.evaluation.dataset.enums import DatasetSplit

import paired_agent_evaluation.composition.builder as composition_builder
import paired_agent_evaluation.experiment_control as control
import paired_agent_evaluation.experiment_control.authorization as control_authorization
import paired_agent_evaluation.experiment_control.freeze as control_freeze
from paired_agent_evaluation.adapters.reproducibility import RuntimeIdentity
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.composition import EvaluationPaths, prepare_run
from paired_agent_evaluation.domain.manifests import ExperimentManifest

TEST_CLAIM_FILENAME = "test-claim.json"


class _StubSettings:
    """Provide deterministic settings used while preparing control fixtures."""

    def __init__(self, **_: object) -> None:
        self.retrieval_backend = "qdrant"
        self.qdrant_collection = "phase3_enterprise_kb"
        self.openai_model = "gpt-5.6"


@pytest.fixture
def control_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EvaluationPaths:
    """Isolate manifests, freezes, and claims from repository state."""
    real = EvaluationPaths.discover()
    isolated_paths = EvaluationPaths(
        repository=real.repository,
        project=real.project,
        artifacts=tmp_path / "artifacts",
        release=tmp_path / "release",
        configs=real.configs,
    )
    monkeypatch.setattr(EvaluationPaths, "discover", lambda: isolated_paths)
    monkeypatch.setattr(composition_builder, "Settings", _StubSettings)
    monkeypatch.setattr(
        composition_builder,
        "capture_runtime_identity",
        lambda _: RuntimeIdentity(
            runtime_settings_sha256="1" * 64,
            tool_schema_sha256="2" * 64,
            qdrant_snapshot_sha256="3" * 64,
            qdrant_point_count=1,
        ),
    )
    monkeypatch.setattr(control_freeze, "HARNESS_MANIFEST", tmp_path / "harness-freeze.json")
    claim_path = tmp_path / TEST_CLAIM_FILENAME
    monkeypatch.setattr(control_freeze, "TEST_EXECUTION_CLAIM", claim_path)
    monkeypatch.setattr(control_authorization, "TEST_EXECUTION_CLAIM", claim_path)
    monkeypatch.setattr(control_freeze, "verify_harness_readiness", lambda paths: None)
    return isolated_paths


def _complete_validation(paths: EvaluationPaths, run_id: str) -> None:
    """Persist the minimum finalized validation evidence required for freezing."""
    _, _, manifest, _ = prepare_run(run_id=run_id, split=DatasetSplit.VALIDATION)
    completed = manifest.model_copy(
        update={
            "status": "scored",
            "accepted_observations": manifest.expected_observations,
        }
    )
    atomic_json(
        paths.run_root(run_id) / "run-manifest.json",
        completed.model_dump(mode="json"),
    )
    atomic_json(
        paths.run_root(run_id) / "summary.json",
        {
            "run_id": run_id,
            "split": "validation",
            "primary_results_final": True,
        },
    )


def test_harness_freeze_pins_validation_and_one_test_identity(
    control_paths: EvaluationPaths,
) -> None:
    """Bind a verified harness freeze to validation and one test identity."""
    _complete_validation(control_paths, "run_validation_complete")

    written = control.write_harness_freeze(
        control_paths,
        validation_run_id="run_validation_complete",
        test_run_id="run_test_registered",
    )
    verified = control.verify_harness_freeze(control_paths)

    assert verified == written
    assert verified.preregistered_test_run_id == "run_test_registered"
    assert verified.validation_run_id == "run_validation_complete"


def test_harness_freeze_requires_completed_validation(control_paths: EvaluationPaths) -> None:
    """Reject harness freezing without finalized validation evidence."""
    with pytest.raises(ValueError, match="Validation must have"):
        control.write_harness_freeze(
            control_paths,
            validation_run_id="run_validation_missing",
            test_run_id="run_test_registered",
        )


def test_harness_verification_rejects_source_drift(
    control_paths: EvaluationPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a freeze after its committed source files change."""
    _complete_validation(control_paths, "run_validation_drift")
    control.write_harness_freeze(
        control_paths,
        validation_run_id="run_validation_drift",
        test_run_id="run_test_drift",
    )
    monkeypatch.setattr(control_freeze, "source_hashes", lambda paths: {"changed.py": "0" * 64})

    with pytest.raises(ValueError, match="source files changed"):
        control.verify_harness_freeze(control_paths)


def test_test_authorization_is_exact_and_consumed_once(
    control_paths: EvaluationPaths,
) -> None:
    """Authorize only the preregistered test identity and consume it once."""
    _complete_validation(control_paths, "run_validation_gate")
    control.write_harness_freeze(
        control_paths,
        validation_run_id="run_validation_gate",
        test_run_id="run_test_once",
    )

    with pytest.raises(ValueError, match="does not match"):
        control.claim_test_execution(control_paths, run_id="run_test_different")

    claim = control.claim_test_execution(control_paths, run_id="run_test_once")
    claim_path = control_paths.artifacts.parent / TEST_CLAIM_FILENAME
    claim_payload = json.loads(claim_path.read_text())
    assert claim_payload["test_run_id"] == claim.test_run_id

    with pytest.raises(ValueError, match="already been consumed"):
        control.claim_test_execution(control_paths, run_id="run_test_once")


def test_prior_test_manifest_blocks_the_preregistered_test_run(
    control_paths: EvaluationPaths,
) -> None:
    """Block authorization when any prior test manifest proves execution occurred."""
    validation_id = "run_validation_prior"
    _complete_validation(control_paths, validation_id)
    control.write_harness_freeze(
        control_paths,
        validation_run_id=validation_id,
        test_run_id="run_test_registered_after_prior",
    )
    validation_manifest_path = control_paths.run_root(validation_id) / "run-manifest.json"
    prior = ExperimentManifest.model_validate_json(
        validation_manifest_path.read_text(encoding="utf-8")
    ).model_copy(update={"run_id": "run_test_prior", "split": "test"})
    prior_root = control_paths.run_root(prior.run_id)
    prior_root.mkdir(parents=True)
    atomic_json(prior_root / "run-manifest.json", prior.model_dump(mode="json"))

    with pytest.raises(ValueError, match="already executed: run_test_prior"):
        control.claim_test_execution(
            control_paths,
            run_id="run_test_registered_after_prior",
        )
