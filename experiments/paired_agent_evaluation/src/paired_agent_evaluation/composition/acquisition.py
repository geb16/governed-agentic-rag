"""Compose concrete adapters and execute evaluation acquisition.

References:
    [1] Alistair Cockburn, "Hexagonal Architecture."
        https://alistair.cockburn.us/hexagonal-architecture
"""

from __future__ import annotations

from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournalStore,
)
from paired_agent_evaluation.adapters.storage.filesystem import RawFilesystemStore, atomic_json
from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.composition.builder import prepare_run
from paired_agent_evaluation.composition.identity import load_experiment_config
from paired_agent_evaluation.composition.paths import EvaluationPaths
from paired_agent_evaluation.domain.executions import Condition
from paired_agent_evaluation.domain.manifests import ExperimentManifest, TestExecutionClaim
from paired_agent_evaluation.experiment_control import claim_test_execution


def _acquire(
    *,
    run_id: str,
    split: DatasetSplit,
    test_claim: TestExecutionClaim | None = None,
) -> ExperimentManifest:
    """Runs acquisition through concrete adapters and records completion.

    Raises:
        ValueError: If protected test acquisition lacks a matching claim.
        RuntimeError: If an observation cannot be safely executed or resumed.
    """
    paths, schedule, manifest, settings = prepare_run(run_id=run_id, split=split)
    config = load_experiment_config(paths)
    cases = EvaluationDataset(paths.repository).cases(split)
    run_root = paths.run_root(run_id)
    if split == DatasetSplit.TEST:
        if test_claim is None or test_claim.test_run_id != run_id:
            raise ValueError("Test acquisition requires its consumed execution claim")
        atomic_json(run_root / "test-execution-claim.json", test_claim.model_dump(mode="json"))
    store = RawFilesystemStore(run_root / "raw" / "observations")
    executions = AcquisitionRunner(
        runners={
            Condition.BASELINE: BaselineSystemRunner(settings),
            Condition.GOVERNED: GovernedSystemRunner(settings),
        },
        store=store,
        attempts=FilesystemAttemptJournalStore(run_root / "work"),
        max_pre_acceptance_attempts=config.max_pre_acceptance_attempts,
    ).run(schedule, cases)
    accepted = sum(item.request_accepted for item in executions)
    completed = manifest.model_copy(
        update={
            "status": "acquired",
            "accepted_observations": accepted,
            "invalid_observations": len(executions) - accepted,
        }
    )
    atomic_json(run_root / "run-manifest.json", completed.model_dump(mode="json"))
    return completed


def acquire(*, run_id: str, split: DatasetSplit) -> ExperimentManifest:
    """Acquires non-test observations through the resumable harness.

    Raises:
        ValueError: If split is the protected test split.
    """
    if split == DatasetSplit.TEST:
        raise ValueError("Test acquisition requires the preregistered one-time execution gate")
    return _acquire(run_id=run_id, split=split)


def acquire_preregistered_test(*, run_id: str) -> ExperimentManifest:
    """Consumes the preregistered test claim, then acquires the test split."""
    paths = EvaluationPaths.discover()
    claim = claim_test_execution(paths, run_id=run_id)
    return _acquire(run_id=run_id, split=DatasetSplit.TEST, test_claim=claim)
