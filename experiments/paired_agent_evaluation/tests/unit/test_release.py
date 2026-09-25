"""Verify release sealing, sanitization, and content-integrity enforcement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import paired_agent_evaluation.release.sealing as release_sealing
import paired_agent_evaluation.release.verification as release_verification
from paired_agent_evaluation.domain.manifests import ExperimentManifest
from paired_agent_evaluation.release import (
    RELEASE_FILES,
    seal_corrective_release,
    seal_run,
    verify_release,
)
from paired_agent_evaluation.release.artifacts import read_payload, sha256_file


def _write_complete_run(root: Path, *, split: str = "test") -> None:
    """Create the minimal finalized artifact set accepted by release sealing."""
    for name in RELEASE_FILES:
        path = root / name
        payload: object
        if name == "run-manifest.json":
            payload = {
                "run_id": "run_test",
                "split": split,
                "status": "scored",
                "completed_at": "2026-09-08T12:00:00Z",
                "phase3_freeze_id": "phase3-baseline-v5",
                "phase3_aggregate_sha256": "a" * 64,
                "phase4_freeze_id": "phase4-governance-v7",
                "phase4_aggregate_sha256": "b" * 64,
                "phase5_freeze_id": "phase5-evaluation-v6",
                "phase5_aggregate_sha256": "c" * 64,
                "model_identifier": "test-model",
                "retrieval_backend": "qdrant",
                "qdrant_collection": "test",
                "configuration_sha256": "d" * 64,
                "runtime_settings_sha256": "1" * 64,
                "tool_schema_sha256": "2" * 64,
                "qdrant_snapshot_sha256": "3" * 64,
                "qdrant_point_count": 1,
                "schedule_sha256": "e" * 64,
                "blinding_plan_sha256": "f" * 64,
                "expected_observations": 1,
                "accepted_observations": 1,
                "package_versions": {"harness": "1.0.0"},
            }
        elif name == "test-execution-claim.json":
            payload = {
                "schema_version": 1,
                "test_run_id": "run_test",
                "harness_freeze_id": "paired-agent-evaluation-harness-v1",
                "harness_aggregate_sha256": "a" * 64,
                "validation_run_id": "run_validation",
                "claimed_at": "2026-09-08T12:00:00Z",
            }
        elif name == "summary.json":
            payload = {"primary_results_final": True}
        elif name == "secondary-ragas.jsonl":
            payload = {"api_key": "secret"}
        else:
            payload = []
        if name == "report.html":
            path.write_text("<!doctype html><title>Report</title>\n", encoding="utf-8")
        elif name.endswith(".jsonl"):
            path.write_text(json.dumps({"value": payload}) + "\n", encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")


def test_release_is_sanitized_closed_and_content_addressed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanitize sensitive values, seal once, and detect post-seal mutation."""
    run_root = tmp_path / "run"
    release_root = tmp_path / "release"
    run_root.mkdir()
    _write_complete_run(run_root)
    monkeypatch.setattr(release_sealing, "verify_primary_artifacts", lambda *_: None)
    manifest = seal_run(run_root=run_root, release_root=release_root)
    assert manifest == verify_release(release_root)
    released = json.loads((release_root / "secondary-ragas.jsonl").read_text())
    assert released["value"]["api_key"] == "[REDACTED]"
    with pytest.raises(ValueError, match="empty"):
        seal_run(run_root=run_root, release_root=release_root)
    (release_root / "summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_release(release_root)


def test_release_readme_placeholder_does_not_block_sealing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allow sealing into the versioned directory containing its tracked README."""
    run_root = tmp_path / "run"
    release_root = tmp_path / "release"
    run_root.mkdir()
    release_root.mkdir()
    (release_root / "README.md").write_text("placeholder\n", encoding="utf-8")
    _write_complete_run(run_root)
    monkeypatch.setattr(release_sealing, "verify_primary_artifacts", lambda *_: None)

    manifest = seal_run(run_root=run_root, release_root=release_root)

    assert manifest.run_id == "run_test"
    assert (release_root / "README.md").is_file()
    assert manifest == verify_release(release_root)


def test_corrective_release_preserves_v1_and_records_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-derive v2 without mutating the source run or sealed v1."""
    run_root = tmp_path / "run"
    v1_root = tmp_path / "v1"
    v2_root = tmp_path / "v2"
    run_root.mkdir()
    _write_complete_run(run_root)
    monkeypatch.setattr(release_sealing, "verify_primary_artifacts", lambda *_: None)
    v1 = seal_run(run_root=run_root, release_root=v1_root)
    v1_manifest_sha256 = sha256_file(v1_root / "manifest.json")
    derived_names = {
        "raw-results.jsonl",
        "normalized.jsonl",
        "review-packet.jsonl",
        "resolved-adjudications.jsonl",
        "scores.jsonl",
        "estimates.json",
        "paired-differences.json",
        "summary.json",
    }
    derived = {name: read_payload(v1_root / name) for name in derived_names}
    derived["normalized.jsonl"] = [{"terminal_error_code": "fabricated_citation"}]
    monkeypatch.setattr(release_sealing, "derive_primary_artifacts", lambda **_: derived)
    monkeypatch.setattr(release_sealing, "render_html_report", lambda *_: "<p>corrected</p>\n")

    v2 = seal_corrective_release(
        run_root=run_root,
        prior_release_root=v1_root,
        release_root=v2_root,
        release_id="paired-agent-evaluation-v2",
        correction_id="baseline-safety-terminal-error-v1",
        correction_summary="Normalize baseline safety blocks.",
    )

    correction = read_payload(v2_root / "correction.json")
    assert v2 == verify_release(v2_root)
    assert correction["supersedes_aggregate_sha256"] == v1.aggregate_sha256
    assert "normalized.jsonl" in correction["changed_files"]
    assert sha256_file(v1_root / "manifest.json") == v1_manifest_sha256


def test_corrective_release_cannot_overwrite_prior(tmp_path: Path) -> None:
    """Reject a corrective destination that aliases its superseded release."""
    release_root = tmp_path / "v1"

    with pytest.raises(ValueError, match="must not overwrite"):
        seal_corrective_release(
            run_root=tmp_path / "run",
            prior_release_root=release_root,
            release_root=release_root,
            release_id="paired-agent-evaluation-v2",
            correction_id="test-correction",
            correction_summary="Test correction.",
        )


def test_corrective_release_rejects_noop_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a no-op correction without leaving a partial release directory."""
    run_root = tmp_path / "run"
    v1_root = tmp_path / "v1"
    v2_root = tmp_path / "v2"
    run_root.mkdir()
    _write_complete_run(run_root)
    monkeypatch.setattr(release_sealing, "verify_primary_artifacts", lambda *_: None)
    seal_run(run_root=run_root, release_root=v1_root)
    derived_names = {
        "raw-results.jsonl",
        "normalized.jsonl",
        "review-packet.jsonl",
        "resolved-adjudications.jsonl",
        "scores.jsonl",
        "estimates.json",
        "paired-differences.json",
        "summary.json",
    }
    derived = {name: read_payload(v1_root / name) for name in derived_names}
    monkeypatch.setattr(release_sealing, "derive_primary_artifacts", lambda **_: derived)
    monkeypatch.setattr(
        release_sealing,
        "render_html_report",
        lambda *_: read_payload(v1_root / "report.html"),
    )

    with pytest.raises(ValueError, match="no changed artifacts"):
        seal_corrective_release(
            run_root=run_root,
            prior_release_root=v1_root,
            release_root=v2_root,
            release_id="paired-agent-evaluation-v2",
            correction_id="test-correction",
            correction_summary="Test correction.",
        )

    assert not v2_root.exists()


def test_incomplete_or_unadjudicated_run_cannot_be_sealed(tmp_path: Path) -> None:
    """Reject release creation when required finalized artifacts are absent."""
    run_root = tmp_path / "run"
    run_root.mkdir()
    with pytest.raises(ValueError, match="missing"):
        seal_run(run_root=run_root, release_root=tmp_path / "release")


def test_validation_split_cannot_be_sealed(tmp_path: Path) -> None:
    """The test split is not a tuning set; only it may ever be sealed."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_complete_run(run_root, split="validation")
    with pytest.raises(ValueError, match="test-split"):
        seal_run(run_root=run_root, release_root=tmp_path / "release")


def test_derived_artifact_drift_cannot_be_sealed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a scored run when recomputation disagrees with a primary artifact."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_complete_run(run_root)
    monkeypatch.setattr(
        release_verification,
        "derive_primary_artifacts",
        lambda **_: {"summary.json": {"primary_results_final": True, "trusted": True}},
    )

    with pytest.raises(ValueError, match=r"Primary derived artifacts.*summary\.json"):
        seal_run(run_root=run_root, release_root=tmp_path / "release")


def test_visual_report_drift_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require the sealed visual report to match authoritative primary JSON."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    _write_complete_run(run_root)
    manifest = ExperimentManifest.model_validate_json(
        (run_root / "run-manifest.json").read_text(encoding="utf-8")
    )
    summary = {
        "run_id": "run_test",
        "split": "test",
        "accepted_observations": 1,
        "invalid_observations": 0,
        "pending_metric_contributions": 0,
        "review_items": 0,
        "primary_results_final": True,
    }
    (run_root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(
        release_verification,
        "derive_primary_artifacts",
        lambda **_: {
            "summary.json": summary,
            "estimates.json": [],
            "paired-differences.json": [],
        },
    )

    with pytest.raises(ValueError, match=r"Primary derived artifacts.*report\.html"):
        release_verification.verify_primary_artifacts(run_root, manifest)
