"""Prepare reproducible evaluation runs from frozen inputs.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.1.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.evaluation.dataset.enums import DatasetSplit

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.reproducibility import capture_runtime_identity
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.application.adjudication import BlindingPlan, create_blinding_plan
from paired_agent_evaluation.application.scheduling import build_schedule
from paired_agent_evaluation.composition.identity import (
    build_manifest,
    configuration_identity,
    load_experiment_config,
    load_freeze,
    validate_existing_run,
)
from paired_agent_evaluation.composition.paths import EvaluationPaths, validate_run_id
from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.manifests import ExperimentManifest


def _load_or_create_blinding_plan(
    *,
    run_root: Path,
    expected_ids: list[str],
) -> BlindingPlan:
    """Loads a matching plan or creates one for a new managed run."""
    # Kept local to preparation so private assignments never cross its boundary.
    manifest_path = run_root / "run-manifest.json"
    blinding_path = run_root / "blinding-plan.json"
    if manifest_path.is_file():
        if not blinding_path.is_file():
            raise ValueError("Existing run is missing its private blinding plan")
        plan = BlindingPlan.model_validate_json(blinding_path.read_text(encoding="utf-8"))
        if set(plan.assignments) != set(expected_ids):
            raise ValueError("Existing run blinding plan does not match the schedule")
        return plan
    if run_root.exists() and any(run_root.iterdir()):
        raise ValueError("Run directory exists without a managed manifest")
    run_root.mkdir(parents=True, exist_ok=True)
    plan = create_blinding_plan(expected_ids)
    atomic_json(blinding_path, plan.model_dump(mode="json"))
    return plan


def prepare_run(
    *,
    run_id: str,
    split: DatasetSplit,
) -> tuple[EvaluationPaths, list[ScheduledExecution], ExperimentManifest, Settings]:
    """Creates or validates the reproducibility boundary for one run.

    Preparation binds frozen inputs, configuration, runtime identity, schedule, and
    private blinding assignments. Resumption succeeds only without identity drift.

    Args:
        run_id: Valid artifact identity beginning with run_.
        split: Frozen dataset split to prepare.

    Returns:
        Paths, schedule, persisted manifest, and experiment settings.

    Raises:
        ValueError: If configuration or persisted run identity has drifted.
        OSError: If required artifacts cannot be read or written.
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
        _env_file=paths.repository / ".env",  # pyright: ignore[reportCallIssue]
        execution_profile="experiment",
        experiment_run_id=run_id,
        experiment_manifest_dir=run_root / "system-manifests",
    )
    if settings.retrieval_backend != config.required_retrieval_backend:
        raise ValueError("Configured retrieval backend violates experiment.json")

    phase3 = load_freeze(paths.repository / "docs" / "phase-3-baseline" / "freeze-manifest.json")
    phase4 = load_freeze(paths.repository / "docs" / "phase-4-governance" / "freeze-manifest.json")
    phase5 = dataset.freeze_identity()
    manifest_path = run_root / "run-manifest.json"
    schedule_path = run_root / "schedule.json"
    plan = _load_or_create_blinding_plan(
        run_root=run_root,
        expected_ids=[item.key.observation_id for item in schedule],
    )
    manifest = build_manifest(
        run_id=run_id,
        split=split.value,
        settings=settings,
        phase3=phase3,
        phase4=phase4,
        phase5=phase5,
        configuration_sha256=configuration_identity(
            paths,
            phase3=phase3,
            phase4=phase4,
            phase5=phase5,
        ),
        runtime_identity=capture_runtime_identity(settings).model_dump(),
        schedule=schedule,
        blinding_plan=plan,
    )
    if manifest_path.is_file():
        existing = validate_existing_run(
            manifest_path=manifest_path,
            schedule_path=schedule_path,
            expected=manifest,
        )
        return paths, schedule, existing, settings
    atomic_json(schedule_path, [item.model_dump(mode="json") for item in schedule])
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    return paths, schedule, manifest, settings
