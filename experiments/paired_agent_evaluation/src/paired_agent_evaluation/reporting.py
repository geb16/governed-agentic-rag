"""Derive and persist reproducible evaluation reports from run artifacts.

Reporting verifies frozen identities before normalization, blinded adjudication,
scoring, bootstrap estimation, summary generation, and optional secondary grading.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.1 and 2.13.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
    [2] Ragas, "Faithfulness."
        https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
    [3] Python Software Foundation, "asyncio — Asynchronous I/O."
        https://docs.python.org/3/library/asyncio.html
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.models import EvaluationCase, ScoringRubric
from pydantic import TypeAdapter

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.adapters.storage.filesystem import (
    JsonlStore,
    RawFilesystemStore,
    atomic_json,
    sha256_json,
)
from paired_agent_evaluation.adapters.telemetry import project_trace_facts
from paired_agent_evaluation.application.adjudication import (
    BlindingPlan,
    apply_route_review,
    build_review_item,
    order_review_items,
    resolve_reviews,
)
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.application.scoring import score_all
from paired_agent_evaluation.application.statistics import (
    estimate_condition,
    estimate_paired_difference,
    registered_strata,
)
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.executions import ScheduledExecution
from paired_agent_evaluation.domain.manifests import ExperimentManifest
from paired_agent_evaluation.domain.observations import AcceptanceStatus, NormalizedObservation
from paired_agent_evaluation.domain.scores import (
    Adjudication,
    Estimate,
    MetricContribution,
    PairedDifference,
    ResolvedAdjudication,
    SecondaryGrade,
)
from paired_agent_evaluation.visual_report import write_html_report


def _load_adjudications(run_root: Path) -> dict[str, ResolvedAdjudication]:
    """Loads reviewer files and applies any explicit disagreement resolutions."""
    review_dir = run_root / "adjudication"
    reviews = (
        [
            item
            for path in sorted(review_dir.glob("reviewer-*.jsonl"))
            for item in JsonlStore.read(path, Adjudication)
        ]
        if review_dir.exists()
        else []
    )
    resolution_path = review_dir / "resolutions.jsonl"
    resolutions = (
        JsonlStore.read(resolution_path, ResolvedAdjudication) if resolution_path.is_file() else []
    )
    return resolve_reviews(reviews, resolutions=resolutions)


def _validate_schedule(
    payload: Any,
    observation_ids: Sequence[str],
    *,
    expected_sha256: str,
    expected_observations: int,
) -> None:
    """Validates schedule integrity, cardinality, and observation membership.

    Raises:
        ValueError: If the schedule digest or count differs from the manifest, its
            schema is invalid, or raw observation identities are not an exact set.
    """
    if sha256_json(payload) != expected_sha256:
        raise ValueError("Run schedule has changed")
    schedule = TypeAdapter(list[ScheduledExecution]).validate_python(payload)
    scheduled_ids = [item.key.observation_id for item in schedule]
    if len(schedule) != expected_observations or len(observation_ids) != expected_observations:
        raise ValueError("Observation count does not match the run manifest")
    if len(set(observation_ids)) != len(observation_ids) or set(observation_ids) != set(
        scheduled_ids
    ):
        raise ValueError("Raw observation identities do not match the run schedule")


def _build_estimates(
    contributions: list[MetricContribution],
    cases: list[EvaluationCase],
    rubric: ScoringRubric,
    reporting: dict[str, Any],
) -> tuple[list[Estimate], list[PairedDifference]]:
    """Builds condition estimates and paired effects for every metric and stratum."""
    case_map = {case.case_id: case for case in cases}
    estimates = []
    differences = []
    for stratum, predicate, stratify_by_category, category_macro in registered_strata(cases):
        for definition in rubric.metrics:
            for condition in ("baseline", "governed"):
                estimates.append(
                    estimate_condition(
                        contributions,
                        case_map,
                        metric_id=definition.metric_id,
                        condition=condition,
                        stratum=stratum,
                        include_case=predicate,
                        replicates=int(reporting["bootstrap_replicates"]),
                        seed=int(reporting["bootstrap_seed"]),
                        minimum_valid=int(reporting["minimum_valid_bootstrap_replicates"]),
                        stratify_by_category=stratify_by_category,
                        category_macro=category_macro,
                    )
                )
            differences.append(
                estimate_paired_difference(
                    contributions,
                    case_map,
                    metric_id=definition.metric_id,
                    stratum=stratum,
                    include_case=predicate,
                    replicates=int(reporting["bootstrap_replicates"]),
                    seed=int(reporting["bootstrap_seed"]),
                    minimum_valid=int(reporting["minimum_valid_bootstrap_replicates"]),
                    stratify_by_category=stratify_by_category,
                    category_macro=category_macro,
                )
            )
    return estimates, differences


def _summary(
    run_id: str,
    split: DatasetSplit,
    observations: list[NormalizedObservation],
    resolved: dict[str, ResolvedAdjudication],
    review_items: list[Any],
    pending: int,
) -> dict[str, Any]:
    """Summarizes finality, adjudication, latency, and token usage for a run."""
    return {
        "run_id": run_id,
        "split": split.value,
        "accepted_observations": sum(
            item.acceptance == AcceptanceStatus.ACCEPTED for item in observations
        ),
        "invalid_observations": sum(
            item.acceptance == AcceptanceStatus.INVALID for item in observations
        ),
        "pending_metric_contributions": pending,
        "resolved_adjudications": len(resolved),
        "review_items": len(review_items),
        "primary_results_final": pending == 0,
        "latency_ms_by_condition": {
            condition: [
                item.latency_ms for item in observations if item.key.condition.value == condition
            ]
            for condition in ("baseline", "governed")
        },
        "token_usage_by_condition": {
            condition: {
                "input_tokens": sum(
                    item.input_tokens
                    for item in observations
                    if item.key.condition.value == condition
                ),
                "output_tokens": sum(
                    item.output_tokens
                    for item in observations
                    if item.key.condition.value == condition
                ),
            }
            for condition in ("baseline", "governed")
        },
    }


def derive_primary_artifacts(
    *, paths: EvaluationPaths, run_root: Path, manifest: ExperimentManifest
) -> dict[str, Any]:
    """Derives every primary result artifact from authoritative run inputs.

    The pipeline verifies the private blinding plan and schedule commitment before
    reading raw observations. It then normalizes executions, applies resolved route
    reviews, creates the blinded review packet, scores all observations, and
    computes configured condition and paired estimates. Returned values are not
    persisted, allowing release verification to repeat the derivation independently.

    Args:
        paths: Repository, configuration, and artifact locations.
        run_root: Directory containing the authoritative run inputs.
        manifest: Run identity and integrity commitments.

    Returns:
        Primary artifact payloads keyed by their release filenames.

    Raises:
        ValueError: If an integrity, schema, identity, or scoring invariant fails.
        OSError: If a required run, dataset, or configuration artifact cannot be read.
    """

    blinding_plan = BlindingPlan.model_validate_json(
        (run_root / "blinding-plan.json").read_text(encoding="utf-8")
    )
    if sha256_json(blinding_plan.model_dump(mode="json")) != manifest.blinding_plan_sha256:
        raise ValueError("Run blinding plan has changed")
    split = DatasetSplit(manifest.split)
    dataset = EvaluationDataset(paths.repository)
    cases = dataset.cases(split)
    rubric = dataset.rubric()
    raw = RawFilesystemStore(run_root / "raw" / "observations").read_all()
    schedule = json.loads((run_root / "schedule.json").read_text(encoding="utf-8"))
    _validate_schedule(
        schedule,
        [item.key.observation_id for item in raw],
        expected_sha256=manifest.schedule_sha256,
        expected_observations=manifest.expected_observations,
    )
    normalized = [normalize(item, trace_facts=project_trace_facts(item)) for item in raw]
    resolved = _load_adjudications(run_root)
    normalized = [
        apply_route_review(item, plan=blinding_plan, resolved=resolved) for item in normalized
    ]
    by_raw = {item.key.observation_id: item for item in raw}
    review_items_by_observation = {}
    for observation in normalized:
        observation_id = observation.key.observation_id
        review = build_review_item(
            observation,
            plan=blinding_plan,
            query=str(by_raw[observation_id].request["query"]),
            contexts=[item.content for item in by_raw[observation_id].retrieved],
        )
        if review is not None:
            review_items_by_observation[observation_id] = review
    review_items = order_review_items(review_items_by_observation, plan=blinding_plan)
    contributions = score_all(
        cases,
        normalized,
        blinding_plan=blinding_plan,
        adjudications=resolved,
    )
    reporting = json.loads((paths.configs / "reporting.json").read_text(encoding="utf-8"))
    estimates, differences = _build_estimates(contributions, cases, rubric, reporting)
    pending = sum(item.pending_reason is not None for item in contributions)
    return {
        "raw-results.jsonl": raw,
        "normalized.jsonl": normalized,
        "review-packet.jsonl": review_items,
        "resolved-adjudications.jsonl": list(resolved.values()),
        "scores.jsonl": contributions,
        "estimates.json": [item.model_dump(mode="json") for item in estimates],
        "paired-differences.json": [item.model_dump(mode="json") for item in differences],
        "summary.json": _summary(
            manifest.run_id, split, normalized, resolved, review_items, pending
        ),
    }


def score_run(*, run_id: str) -> dict[str, Any]:
    """Derives and persists primary results, report HTML, and manifest status.

    A run remains awaiting adjudication while any metric contribution is pending.
    Only a fully resolved run becomes scored and receives a completion timestamp.

    Args:
        run_id: Existing acquired run to score.

    Returns:
        The persisted summary payload.

    Raises:
        ValueError: If run integrity or scoring invariants fail.
        OSError: If required artifacts cannot be read or outputs cannot be written.
    """
    paths = EvaluationPaths.discover()
    run_root = paths.run_root(run_id)
    manifest_path = run_root / "run-manifest.json"
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    artifacts = derive_primary_artifacts(paths=paths, run_root=run_root, manifest=manifest)
    for name, payload in artifacts.items():
        path = run_root / name
        if name.endswith(".jsonl"):
            JsonlStore.write(path, payload)
        else:
            atomic_json(path, payload)
    write_html_report(run_root)
    summary = artifacts["summary.json"]
    pending = int(summary["pending_metric_contributions"])
    manifest = manifest.model_copy(
        update={
            "status": "scored" if pending == 0 else "awaiting_adjudication",
            "completed_at": datetime.now(UTC) if pending == 0 else None,
        }
    )
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    return summary


async def _grade_ragas(run_id: str) -> list[SecondaryGrade]:
    """Grades answer-bearing executions against retrieved context with Ragas.

    This diagnostic excludes executions without both an answer and context and does
    not alter primary metric artifacts.

    Args:
        run_id: Existing run containing raw observations.

    Returns:
        Persisted secondary faithfulness grades in observation order.

    Raises:
        ValueError: If the secondary grader API key is unavailable.
    """
    from paired_agent_evaluation.adapters.graders import RagasFaithfulnessGrader

    paths = EvaluationPaths.discover()
    run_root = paths.run_root(run_id)
    raw = RawFilesystemStore(run_root / "raw" / "observations").read_all()
    manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
    settings = Settings(_env_file=paths.repository / ".env")
    if settings.openai_api_key is None:
        raise ValueError("RAG_OPENAI_API_KEY is required for secondary Ragas grading")
    grader = RagasFaithfulnessGrader(
        api_key=settings.openai_api_key.get_secret_value(),
        model=str(manifest["model_identifier"]),
    )
    grades = []
    for execution in raw:
        answer = str((execution.response or {}).get("answer") or "")
        contexts = [item.content for item in execution.retrieved]
        if not answer or not contexts:
            continue
        value, reason = await grader.grade(
            query=str(execution.request["query"]), response=answer, contexts=contexts
        )
        grades.append(
            SecondaryGrade(
                observation_id=execution.key.observation_id,
                grader="ragas.Faithfulness",
                grader_version="0.4.3",
                model_identifier=str(manifest["model_identifier"]),
                value=value,
                reason=reason,
            )
        )
    JsonlStore.write(run_root / "secondary-ragas.jsonl", grades)
    return grades


def grade_ragas(*, run_id: str) -> list[SecondaryGrade]:
    """Runs asynchronous secondary Ragas grading from synchronous code."""
    return asyncio.run(_grade_ragas(run_id))
