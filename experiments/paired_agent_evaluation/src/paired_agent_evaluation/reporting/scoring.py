"""Persist primary report artifacts and advance run status.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.13.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from paired_agent_evaluation.adapters.storage.filesystem import JsonlStore, atomic_json
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.manifests import ExperimentManifest
from paired_agent_evaluation.reporting.derivation import derive_primary_artifacts
from paired_agent_evaluation.reporting.visual_report import write_html_report


def score_run(*, run_id: str) -> dict[str, Any]:
    """Derives and persists primary results, report HTML, and manifest status.

    A run remains awaiting adjudication while metric contributions are pending;
    only a fully resolved run receives a scored status and completion timestamp.

    Returns:
        The persisted summary payload.

    Raises:
        ValueError: If run integrity or scoring invariants fail.
        OSError: If required artifacts cannot be read or written.
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
