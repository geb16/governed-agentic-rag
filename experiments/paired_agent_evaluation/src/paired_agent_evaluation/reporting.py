# Phase-6 reporting orchestration over pure application services.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paired_agent_evaluation.adapters.storage.filesystem import (
    JsonlStore,
    RawFilesystemStore,
)
from paired_agent_evaluation.adapters.telemetry import project_trace_facts
from paired_agent_evaluation.application.adjudication import (
    apply_route_review,
    resolve_reviews,
)
from paired_agent_evaluation.application.normalization import normalize
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.scores import (
    Adjudication,
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


def score_run(*, run_id: str) -> dict[str, Any]:
    paths = EvaluationPaths.discover()
    run_root = paths.run_root(run_id)
    manifest_path = run_root / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = RawFilesystemStore(run_root / "raw" / "observations").read_all()
    if len(raw) != int(manifest["expected_observations"]):
        raise ValueError("Raw observation count does not match the run manifest")
    normalized = [normalize(item, trace_facts=project_trace_facts(item)) for item in raw]
    resolved = _load_adjudications(run_root)
    normalized = [apply_route_review(item, run_id=run_id, resolved=resolved) for item in normalized]