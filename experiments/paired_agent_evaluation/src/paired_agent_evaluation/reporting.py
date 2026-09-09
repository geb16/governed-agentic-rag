# Phase-6 reporting orchestration over pure application services.

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

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
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


def _load_adjudications(run_root: Path) -> dict[str, ResolvedAdjudication]:
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


def score_run(*, run_id: str) -> dict[str, Any]:
    paths = EvaluationPaths.discover()
    run_root = paths.run_root(run_id)
    manifest_path = run_root / "run-manifest.json"
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    blinding_plan = BlindingPlan.model_validate_json(
        (run_root / "blinding-plan.json").read_text(encoding="utf-8")
    )
    if sha256_json(blinding_plan.model_dump(mode="json")) != manifest.blinding_plan_sha256:
        raise ValueError("Run blinding plan has changed")
    split = DatasetSplit(manifest.split)
    dataset = Phase5Dataset(paths.repository)
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
    JsonlStore.write(run_root / "raw-results.jsonl", raw)
    JsonlStore.write(run_root / "normalized.jsonl", normalized)
    JsonlStore.write(run_root / "review-packet.jsonl", review_items)
    JsonlStore.write(run_root / "resolved-adjudications.jsonl", list(resolved.values()))
    JsonlStore.write(run_root / "scores.jsonl", contributions)
    atomic_json(run_root / "estimates.json", [item.model_dump(mode="json") for item in estimates])
    atomic_json(
        run_root / "paired-differences.json",
        [item.model_dump(mode="json") for item in differences],
    )
    pending = sum(item.pending_reason is not None for item in contributions)
    summary = _summary(run_id, split, normalized, resolved, review_items, pending)
    atomic_json(run_root / "summary.json", summary)
    manifest = manifest.model_copy(
        update={
            "status": "scored" if pending == 0 else "awaiting_adjudication",
            "completed_at": datetime.now(UTC) if pending == 0 else None,
        }
    )
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    return summary


async def _grade_ragas(run_id: str) -> list[SecondaryGrade]:
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
    return asyncio.run(_grade_ragas(run_id))
