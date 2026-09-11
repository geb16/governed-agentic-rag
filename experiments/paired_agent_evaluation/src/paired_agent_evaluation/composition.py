"""Wire the evaluation harness and establish reproducible run identity.

The composition root binds application ports to concrete adapters, freezes runtime
and input identities, and rejects path escapes or drift when resuming a run.

References:
    [1] Alistair Cockburn, "Hexagonal Architecture."
        https://alistair.cockburn.us/hexagonal-architecture
    [2] NIST, "AI Risk Management Framework Core," Measure 2.1.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
    [3] OWASP, "Input Validation Cheat Sheet."
        https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
"""

from __future__ import annotations

import importlib.metadata
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.reproducibility import capture_runtime_identity
from paired_agent_evaluation.adapters.storage.attempt_journal import (
    FilesystemAttemptJournalStore,
)
from paired_agent_evaluation.adapters.storage.filesystem import (
    RawFilesystemStore,
    atomic_json,
    sha256_json,
)
from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.application.adjudication import BlindingPlan, create_blinding_plan
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import (
    Condition,
    ExperimentConfig,
    ScheduledExecution,
)
from paired_agent_evaluation.domain.manifests import ExperimentManifest, TestExecutionClaim
from paired_agent_evaluation.experiment_control import claim_test_execution


@dataclass(frozen=True, slots=True)
class EvaluationPaths:
    """Locates repository inputs and isolated evaluation artifact roots."""

    repository: Path
    project: Path
    artifacts: Path
    release: Path
    configs: Path

    @classmethod
    def discover(cls) -> EvaluationPaths:
        """Discovers evaluation paths relative to this installed source file."""
        repository = Path(__file__).resolve().parents[4]
        project = repository / "experiments" / "paired_agent_evaluation"
        return cls(
            repository=repository,
            project=project,
            artifacts=repository / "artifacts" / "paired_agent_evaluation",
            release=repository / "data" / "evaluation" / "paired_agent_evaluation" / "v1",
            configs=project / "config",
        )

    def run_root(self, run_id: str) -> Path:
        """Returns the artifact directory for a validated run identifier.

        Raises:
            ValueError: If the identifier could escape or alias the run namespace.
        """
        validate_run_id(run_id)
        return self.artifacts / run_id


def validate_run_id(run_id: str) -> None:
    """Validates a run identifier against the artifact-name allowlist.

    Raises:
        ValueError: If the identifier is empty, malformed, or contains path syntax.
    """

    if re.fullmatch(r"run_[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run_id must match run_[A-Za-z0-9_-]+")


def _json(path: Path) -> Any:
    """Loads one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_experiment_config(paths: EvaluationPaths) -> ExperimentConfig:
    """Loads and validates the preregistered experiment configuration."""

    return ExperimentConfig.model_validate(_json(paths.configs / "experiment.json"))


def _freeze(path: Path) -> dict[str, Any]:
    """Loads a freeze manifest and requires a JSON object."""
    payload = _json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Freeze manifest must be an object: {path}")
    return payload


def _schedule_hash(schedule: list[ScheduledExecution]) -> str:
    """Returns the canonical digest of the serialized schedule."""
    return sha256_json([item.model_dump(mode="json") for item in schedule])


def prepare_run(
    *,
    run_id: str,
    split: DatasetSplit,
) -> tuple[EvaluationPaths, list[ScheduledExecution], ExperimentManifest, Settings]:
    """Creates or validates the reproducibility boundary for one run.

    Preparation resolves the frozen dataset and configuration, builds the paired
    schedule, captures runtime and dependency identity, and persists a private
    blinding plan. Resuming is idempotent only when immutable manifest fields,
    schedule content, and blinding assignments still match current inputs.

    Args:
        run_id: Valid artifact identity beginning with run_.
        split: Frozen dataset split to prepare.

    Returns:
        Paths, schedule, persisted manifest, and experiment settings.

    Raises:
        ValueError: If inputs violate the frozen configuration, an existing run is
            unmanaged or incomplete, or any immutable identity has drifted.
        OSError: If required inputs or run artifacts cannot be read or written.
        importlib.metadata.PackageNotFoundError: If a tracked package is unavailable.
    """

    paths = EvaluationPaths.discover()
    validate_run_id(run_id)
    config = load_experiment_config(paths)
    dataset = EvaluationDataset(paths.repository)
    cases = dataset.cases(split)
    rubric = dataset.rubric()
    if rubric.repetitions_per_case != config.repetitions_per_case:
        raise ValueError("Experiment repetitions drift from the frozen rubric")
    schedule = build_schedule(
        cases,
        repetitions=config.repetitions_per_case,
        seed=config.condition_order_seed,
    )
    run_root = paths.run_root(run_id)
    settings = Settings(
        _env_file=paths.repository / ".env",
        execution_profile="experiment",
        experiment_run_id=run_id,
        experiment_manifest_dir=run_root / "system-manifests",
    )
    if settings.retrieval_backend != config.required_retrieval_backend:
        raise ValueError("Configured retrieval backend violates experiment.json")
    runtime_identity = capture_runtime_identity(settings)
    phase3 = _freeze(paths.repository / "docs" / "phase-3-freeze-manifest.json")
    phase4 = _freeze(paths.repository / "docs" / "phase-4-freeze-manifest.json")
    phase5 = dataset.freeze_identity()
    configuration = {
        name: _json(paths.configs / name)
        for name in ("experiment.json", "graders.json", "reporting.json")
    }
    configuration["freeze_aggregates"] = {
        "phase3": phase3["aggregate_sha256"],
        "phase4": phase4["aggregate_sha256"],
        "phase5": phase5["aggregate_sha256"],
    }
    manifest_path = run_root / "run-manifest.json"
    schedule_path = run_root / "schedule.json"
    blinding_path = run_root / "blinding-plan.json"
    expected_ids = [item.key.observation_id for item in schedule]
    if manifest_path.is_file():
        if not blinding_path.is_file():
            raise ValueError("Existing run is missing its private blinding plan")
        blinding_plan = BlindingPlan.model_validate_json(blinding_path.read_text(encoding="utf-8"))
        if set(blinding_plan.assignments) != set(expected_ids):
            raise ValueError("Existing run blinding plan does not match the schedule")
    else:
        if run_root.exists() and any(run_root.iterdir()):
            raise ValueError("Run directory exists without a managed manifest")
        run_root.mkdir(parents=True, exist_ok=True)
        blinding_plan = create_blinding_plan(expected_ids)
        atomic_json(blinding_path, blinding_plan.model_dump(mode="json"))
    package_names = ["governed-agentic-rag", "governed-agentic-rag-paired-evaluation", "ragas"]
    versions = {name: importlib.metadata.version(name) for name in package_names}
    manifest = ExperimentManifest(
        run_id=run_id,
        split=split.value,
        status="prepared",
        phase3_freeze_id=str(phase3["freeze_id"]),
        phase3_aggregate_sha256=str(phase3["aggregate_sha256"]),
        phase4_freeze_id=str(phase4["freeze_id"]),
        phase4_aggregate_sha256=str(phase4["aggregate_sha256"]),
        phase5_freeze_id=str(phase5["freeze_id"]),
        phase5_aggregate_sha256=str(phase5["aggregate_sha256"]),
        model_identifier=settings.openai_model,
        retrieval_backend=settings.retrieval_backend,
        qdrant_collection=settings.qdrant_collection,
        configuration_sha256=sha256_json(configuration),
        **runtime_identity.model_dump(),
        schedule_sha256=_schedule_hash(schedule),
        blinding_plan_sha256=sha256_json(blinding_plan.model_dump(mode="json")),
        expected_observations=len(schedule),
        package_versions=versions,
    )
    if manifest_path.is_file():
        existing = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        immutable = (
            "run_id",
            "split",
            "phase3_aggregate_sha256",
            "phase4_aggregate_sha256",
            "phase5_aggregate_sha256",
            "model_identifier",
            "retrieval_backend",
            "qdrant_collection",
            "configuration_sha256",
            "runtime_settings_sha256",
            "tool_schema_sha256",
            "qdrant_snapshot_sha256",
            "qdrant_point_count",
            "schedule_sha256",
            "blinding_plan_sha256",
            "expected_observations",
            "package_versions",
        )
        drift = [name for name in immutable if getattr(existing, name) != getattr(manifest, name)]
        if drift:
            raise ValueError(f"Existing run manifest drift: {', '.join(drift)}")
        if (
            not schedule_path.is_file()
            or sha256_json(_json(schedule_path)) != manifest.schedule_sha256
        ):
            raise ValueError("Existing run schedule is missing or has changed")
        return paths, schedule, existing, settings
    atomic_json(schedule_path, [item.model_dump(mode="json") for item in schedule])
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    return paths, schedule, manifest, settings


def _acquire(
    *,
    run_id: str,
    split: DatasetSplit,
    test_claim: TestExecutionClaim | None = None,
) -> ExperimentManifest:
    """Runs acquisition through concrete adapters and records completion.

    Test acquisition additionally requires a matching consumed execution claim,
    which is persisted before either evaluated system is invoked.

    Args:
        run_id: Prepared run identity.
        split: Dataset split to acquire.
        test_claim: Consumed one-time claim required for the test split.

    Returns:
        The run manifest updated with acquisition counts.

    Raises:
        ValueError: If test acquisition lacks a matching claim or preparation fails.
        RuntimeError: If acquisition cannot safely execute or resume an observation.
    """
    paths, schedule, manifest, settings = prepare_run(run_id=run_id, split=split)
    config = load_experiment_config(paths)
    cases = EvaluationDataset(paths.repository).cases(split)
    run_root = paths.run_root(run_id)
    if split == DatasetSplit.TEST:
        if test_claim is None or test_claim.test_run_id != run_id:
            raise ValueError("Test acquisition requires its consumed execution claim")
        atomic_json(
            run_root / "test-execution-claim.json",
            test_claim.model_dump(mode="json"),
        )
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
