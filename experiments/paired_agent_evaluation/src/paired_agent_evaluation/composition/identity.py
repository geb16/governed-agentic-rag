"""Build and verify content-addressed evaluation run identities.

References:
    [1] NIST, "FIPS 180-4: Secure Hash Standard."
        https://doi.org/10.6028/NIST.FIPS.180-4
    [2] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

from app.core.config import Settings

from paired_agent_evaluation.adapters.storage.filesystem import sha256_json
from paired_agent_evaluation.application.adjudication import BlindingPlan
from paired_agent_evaluation.composition.paths import EvaluationPaths
from paired_agent_evaluation.domain.executions import ExperimentConfig, ScheduledExecution
from paired_agent_evaluation.domain.manifests import ExperimentManifest

IMMUTABLE_MANIFEST_FIELDS = (
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


def load_json(path: Path) -> Any:
    """Loads one UTF-8 JSON artifact."""
    return json.loads(path.read_text(encoding="utf-8"))


def load_experiment_config(paths: EvaluationPaths) -> ExperimentConfig:
    """Loads and validates the preregistered experiment configuration."""
    return ExperimentConfig.model_validate(load_json(paths.configs / "experiment.json"))


def load_freeze(path: Path) -> dict[str, Any]:
    """Loads a freeze manifest and requires a JSON object.

    Raises:
        ValueError: If the manifest root is not a JSON object.
    """
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"Freeze manifest must be an object: {path}")
    return payload


def schedule_hash(schedule: list[ScheduledExecution]) -> str:
    """Returns the canonical digest of the serialized schedule."""
    return sha256_json([item.model_dump(mode="json") for item in schedule])


def configuration_identity(
    paths: EvaluationPaths,
    *,
    phase3: dict[str, Any],
    phase4: dict[str, Any],
    phase5: dict[str, Any],
) -> str:
    """Returns a digest binding configuration files to inherited freezes."""
    configuration = {
        name: load_json(paths.configs / name)
        for name in ("experiment.json", "graders.json", "reporting.json")
    }
    configuration["freeze_aggregates"] = {
        "phase3": phase3["aggregate_sha256"],
        "phase4": phase4["aggregate_sha256"],
        "phase5": phase5["aggregate_sha256"],
    }
    return sha256_json(configuration)


def package_versions() -> dict[str, str]:
    """Returns versions of packages that affect evaluation results."""
    names = ("governed-agentic-rag", "governed-agentic-rag-paired-evaluation", "ragas")
    return {name: importlib.metadata.version(name) for name in names}


def build_manifest(
    *,
    run_id: str,
    split: str,
    settings: Settings,
    phase3: dict[str, Any],
    phase4: dict[str, Any],
    phase5: dict[str, Any],
    configuration_sha256: str,
    runtime_identity: dict[str, Any],
    schedule: list[ScheduledExecution],
    blinding_plan: BlindingPlan,
) -> ExperimentManifest:
    """Builds the immutable identity for a prepared evaluation run."""
    return ExperimentManifest(
        run_id=run_id,
        split=split,
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
        configuration_sha256=configuration_sha256,
        **runtime_identity,
        schedule_sha256=schedule_hash(schedule),
        blinding_plan_sha256=sha256_json(blinding_plan.model_dump(mode="json")),
        expected_observations=len(schedule),
        package_versions=package_versions(),
    )


def validate_existing_run(
    *,
    manifest_path: Path,
    schedule_path: Path,
    expected: ExperimentManifest,
) -> ExperimentManifest:
    """Returns an existing manifest after rejecting identity or schedule drift.

    Raises:
        ValueError: If immutable fields or serialized schedule content changed.
    """
    existing = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    drift = [
        name
        for name in IMMUTABLE_MANIFEST_FIELDS
        if getattr(existing, name) != getattr(expected, name)
    ]
    if drift:
        raise ValueError(f"Existing run manifest drift: {', '.join(drift)}")
    if (
        not schedule_path.is_file()
        or sha256_json(load_json(schedule_path)) != expected.schedule_sha256
    ):
        raise ValueError("Existing run schedule is missing or has changed")
    return existing
