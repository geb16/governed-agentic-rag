# Tests for Phase-6 freeze and one-time test-execution controls.

from __future__ import annotations

import json

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


class _StubSettings:
    def __init__(self, **_: object) -> None:
        self.retrieval_backend = "qdrant"
        self.qdrant_collection = "phase3_enterprise_kb"
        self.openai_model = "gpt-5.6"


@pytest.fixture
def control_paths(tmp_path, monkeypatch) -> EvaluationPaths:
    real = EvaluationPaths.discover()
    isolated_paths = EvaluationPaths(
        repository=real.repository,
        project=real.project,
        artifacts=tmp_path / "artifacts",
        release=tmp_path / "release",
        configs=real.configs,
    )
    monkeypatch.setattr(composition_builder.EvaluationPaths, "discover", lambda: isolated_paths)
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
    monkeypatch.setattr(control_freeze, "TEST_EXECUTION_CLAIM", tmp_path / "test-claim.json")
    monkeypatch.setattr(control_authorization, "TEST_EXECUTION_CLAIM", tmp_path / "test-claim.json")
    monkeypatch.setattr(control_freeze, "verify_harness_readiness", lambda paths: None)
    return isolated_paths


def _complete_validation(paths: EvaluationPaths, run_id: str) -> None:
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


# Testing the harness freeze is written and verified correctly,
# and that the test run ID is correctly recorded in the freeze.
def test_harness_freeze_pins_validation_and_one_test_identity(control_paths) -> None:
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


def test_harness_freeze_requires_completed_validation(control_paths) -> None:
    with pytest.raises(ValueError, match="Validation must have"):
        control.write_harness_freeze(
            control_paths,
            validation_run_id="run_validation_missing",
            test_run_id="run_test_registered",
        )


# Testing that the harness freeze verification fails if the source code has
# changed since the freeze was written.
def test_harness_verification_rejects_source_drift(control_paths, monkeypatch) -> None:
    _complete_validation(control_paths, "run_validation_drift")
    control.write_harness_freeze(
        control_paths,
        validation_run_id="run_validation_drift",
        test_run_id="run_test_drift",
    )
    monkeypatch.setattr(control_freeze, "source_hashes", lambda paths: {"changed.py": "0" * 64})

    with pytest.raises(ValueError, match="source files changed"):
        control.verify_harness_freeze(control_paths)


# checking if the test execution claim is only valid for the specific test run ID and
# can only be consumed once.
def test_test_authorization_is_exact_and_consumed_once(control_paths) -> None:
    _complete_validation(control_paths, "run_validation_gate")
    control.write_harness_freeze(
        control_paths,
        validation_run_id="run_validation_gate",
        test_run_id="run_test_once",
    )

    with pytest.raises(ValueError, match="does not match"):
        control.claim_test_execution(control_paths, run_id="run_test_different")

    claim = control.claim_test_execution(control_paths, run_id="run_test_once")
    claim_payload = json.loads(
        (control_paths.repository / control_authorization.TEST_EXECUTION_CLAIM).read_text()
    )
    assert claim_payload["test_run_id"] == claim.test_run_id

    with pytest.raises(ValueError, match="already been consumed"):
        control.claim_test_execution(control_paths, run_id="run_test_once")


# Checking that if a test run has already been executed and recorded in the manifest,
def test_prior_test_manifest_blocks_the_preregistered_test_run(control_paths) -> None:
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
