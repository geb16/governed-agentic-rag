# Phase-6 reporting orchestration over pure application services.


from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.models import EvaluationCase, ScoringRubric

from paired_agent_evaluation.adapters.dataset import Phase5Dataset
from paired_agent_evaluation.adapters.storage.filesystem import (
    JsonlStore,
    RawFilesystemStore,
    atomic_json,
)
from paired_agent_evaluation.adapters.telemetry import project_trace_facts
from paired_agent_evaluation.application.adjudication import (
    apply_route_review,
    build_review_item,
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
from paired_agent_evaluation.domain.observations import AcceptanceStatus, NormalizedObservation
from paired_agent_evaluation.domain.scores import (
    Adjudication,
    Estimate,
    MetricContribution,
    PairedDifference,
    ResolvedAdjudication,
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

def _build_estimates(
    contributions: list[MetricContribution],
    cases: list[EvaluationCase],
    rubric: ScoringRubric,
    reporting: dict[str, Any],
) -> tuple[list[Estimate], list[PairedDifference]]:
    case_map = {case.case_id: case for case in cases}
    estimates = []
    differences = []
    for stratum, predicate in registered_strata(cases):
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    split = DatasetSplit(str(manifest["split"]))
    dataset = Phase5Dataset(paths.repository)
    cases = dataset.cases(split)
    rubric = dataset.rubric()
    raw = RawFilesystemStore(run_root / "raw" / "observations").read_all()
    if len(raw) != int(manifest["expected_observations"]):
        raise ValueError("Raw observation count does not match the run manifest")
    normalized = [normalize(item, trace_facts=project_trace_facts(item)) for item in raw]
    resolved = _load_adjudications(run_root)
    normalized = [apply_route_review(item, run_id=run_id, resolved=resolved) for item in normalized]
    by_raw = {item.key.observation_id: item for item in raw}
    review_items = [
        review
        for observation in normalized
        if (
            review := build_review_item(
                observation,
                run_id=run_id,
                query=str(by_raw[observation.key.observation_id].request["query"]),
                contexts=[
                    item.content for item in by_raw[observation.key.observation_id].retrieved
                ],
            )
        )
        is not None
    ]
    contributions = score_all(cases, normalized, run_id=run_id, adjudications=resolved)
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
    manifest["status"] = "scored" if pending == 0 else "awaiting_adjudication"
    manifest["completed_at"] = datetime.now(UTC).isoformat() if pending == 0 else None
    atomic_json(manifest_path, manifest)
    return summary