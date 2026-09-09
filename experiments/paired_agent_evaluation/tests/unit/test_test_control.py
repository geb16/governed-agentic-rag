# Tests for Phase-6 freeze and one-time test-execution controls.

from __future__ import annotations

from app.evaluation.dataset.enums import DatasetSplit

import paired_agent_evaluation.test_control as control
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.composition import EvaluationPaths, prepare_run


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

