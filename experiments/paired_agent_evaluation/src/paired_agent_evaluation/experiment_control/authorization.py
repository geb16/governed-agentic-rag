"""Atomically consume authorization for one preregistered test run.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.13.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
"""

from __future__ import annotations

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.storage.filesystem import exclusive_json
from paired_agent_evaluation.domain.manifests import ExperimentManifest, TestExecutionClaim
from paired_agent_evaluation.experiment_control.contracts import EvaluationControlPaths
from paired_agent_evaluation.experiment_control.freeze import verify_harness_freeze
from paired_agent_evaluation.experiment_control.policy import TEST_EXECUTION_CLAIM


def _existing_test_runs(paths: EvaluationControlPaths) -> list[str]:
    """Returns sorted test-run identities already present in artifacts."""
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

    Returns:
        The claim binding the test run to its harness and validation evidence.

    Raises:
        ValueError: If authorization is invalid, unsafe, or already consumed.
        OSError: If control artifacts cannot be read or written.
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
