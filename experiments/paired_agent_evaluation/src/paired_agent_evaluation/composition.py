# Composition root for the independently versioned Phase-6 harness.

from __future__ import annotations

import importlib.metadata
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.adapters.storage.filesystem import (
    RawFilesystemStore,
    atomic_json,
    sha256_json,
)
from paired_agent_evaluation.adapters.systems import BaselineSystemRunner, GovernedSystemRunner
from paired_agent_evaluation.application.acquisition import AcquisitionRunner
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.domain.executions import (
    Condition,
    ExperimentConfig,
    ScheduledExecution,
)
from paired_agent_evaluation.domain.manifests import ExperimentManifest


@dataclass(frozen=True, slots=True)
class EvaluationPaths:
    repository: Path
    project: Path
    artifacts: Path
    release: Path
    configs: Path

    @classmethod
    def discover(cls) -> EvaluationPaths:
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
        validate_run_id(run_id)
        return self.artifacts / run_id


def validate_run_id(run_id: str) -> None:
    if re.fullmatch(r"run_[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run_id must match run_[A-Za-z0-9_-]+")

def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_experiment_config(paths: EvaluationPaths) -> ExperimentConfig:
    return ExperimentConfig.model_validate(_json(paths.configs / "experiment.json"))

def _freeze(path: Path) -> dict[str, Any]:
    payload = _json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Freeze manifest must be an object: {path}")
    return payload

def _schedule_hash(schedule: list[ScheduledExecution]) -> str:
    return sha256_json([item.model_dump(mode="json") for item in schedule])


def prepare_run(
    *,
    run_id: str,
    split: DatasetSplit,
) -> tuple[EvaluationPaths, list[ScheduledExecution], ExperimentManifest, Settings]:
    paths = EvaluationPaths.discover()
    validate_run_id(run_id)
    config = load_experiment_config(paths)
    dataset = Phase5Dataset(paths.repository)
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
        schedule_sha256=_schedule_hash(schedule),
        expected_observations=len(schedule),
        package_versions=versions,
    )
    manifest_path = run_root / "run-manifest.json"
    schedule_path = run_root / "schedule.json"
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
            "schedule_sha256",
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
    
    return paths, schedule, manifest, settings


def acquire(*, run_id: str, split: DatasetSplit) -> ExperimentManifest:
    paths, schedule, manifest, settings = prepare_run(run_id=run_id, split=split)
    config = load_experiment_config(paths)
    cases = Phase5Dataset(paths.repository).cases(split)
    run_root = paths.run_root(run_id)
    store = RawFilesystemStore(run_root / "raw" / "observations")
    executions = AcquisitionRunner(
        runners={
            Condition.BASELINE: BaselineSystemRunner(settings),
            Condition.GOVERNED: GovernedSystemRunner(settings),
        },
        store=store,
        workspace=run_root / "work",
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
