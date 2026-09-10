import json

import paired_agent_evaluation.reporting as reporting
from paired_agent_evaluation.adapters.storage.filesystem import atomic_json
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.manifests import ExperimentManifest


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(
        run_id="run_reporting",
        split="validation",
        status="acquired",
        phase3_freeze_id="phase3-baseline-v3",
        phase3_aggregate_sha256="a" * 64,
        phase4_freeze_id="phase4-governance-v3",
        phase4_aggregate_sha256="b" * 64,
        phase5_freeze_id="phase5-evaluation-v2",
        phase5_aggregate_sha256="c" * 64,
        model_identifier="test-model",
        retrieval_backend="qdrant",
        qdrant_collection="test",
        configuration_sha256="d" * 64,
        runtime_settings_sha256="1" * 64,
        tool_schema_sha256="2" * 64,
        qdrant_snapshot_sha256="3" * 64,
        qdrant_point_count=1,
        schedule_sha256="e" * 64,
        blinding_plan_sha256="f" * 64,
        expected_observations=1,
        accepted_observations=1,
        package_versions={"harness": "1.0.0"},
    )


def test_score_run_persists_derived_outputs_report_and_terminal_status(
    tmp_path, monkeypatch
) -> None:
    """Cover reporting orchestration without duplicating pure scoring tests."""

    paths = EvaluationPaths(
        repository=tmp_path,
        project=tmp_path / "project",
        artifacts=tmp_path / "artifacts",
        release=tmp_path / "release",
        configs=tmp_path / "configs",
    )
    run_root = paths.run_root("run_reporting")
    atomic_json(run_root / "run-manifest.json", _manifest().model_dump(mode="json"))
    summary = {
        "run_id": "run_reporting",
        "split": "validation",
        "accepted_observations": 1,
        "invalid_observations": 0,
        "pending_metric_contributions": 0,
        "resolved_adjudications": 0,
        "review_items": 0,
        "primary_results_final": True,
    }
    artifacts = {
        "raw-results.jsonl": [],
        "normalized.jsonl": [],
        "review-packet.jsonl": [],
        "resolved-adjudications.jsonl": [],
        "scores.jsonl": [],
        "estimates.json": [],
        "paired-differences.json": [],
        "summary.json": summary,
    }
    monkeypatch.setattr(reporting.EvaluationPaths, "discover", lambda: paths)
    monkeypatch.setattr(reporting, "derive_primary_artifacts", lambda **_: artifacts)

    assert reporting.score_run(run_id="run_reporting") == summary
    persisted = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "scored"
    assert persisted["completed_at"] is not None
    assert (run_root / "report.html").is_file()
