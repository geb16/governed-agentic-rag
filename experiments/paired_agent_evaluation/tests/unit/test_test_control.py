# Tests for Phase-6 freeze and one-time test-execution controls.

from __future__ import annotations

import json

import pytest
from app.evaluation.dataset.enums import DatasetSplit

import paired_agent_evaluation.composition as composition_module
import paired_agent_evaluation.test_control as control
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.composition import EvaluationPaths, prepare_run


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
    monkeypatch.setattr(composition_module.EvaluationPaths, "discover", lambda: isolated_paths)
    monkeypatch.setattr(composition_module, "Settings", _StubSettings)
    monkeypatch.setattr(control, "HARNESS_MANIFEST", tmp_path / "harness-freeze.json")
    monkeypatch.setattr(control, "TEST_EXECUTION_CLAIM", tmp_path / "test-claim.json")
    monkeypatch.setattr(control, "verify_harness_readiness", lambda paths: None)
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
    monkeypatch.setattr(control, "_source_hashes", lambda paths: {"changed.py": "0" * 64})

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
        (control_paths.repository / control.TEST_EXECUTION_CLAIM).read_text()
    )
    assert claim_payload["test_run_id"] == claim.test_run_id

    with pytest.raises(ValueError, match="already been consumed"):
        control.claim_test_execution(control_paths, run_id="run_test_once")
