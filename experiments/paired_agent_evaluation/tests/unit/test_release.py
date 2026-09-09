import json

import pytest

from paired_agent_evaluation.release import RELEASE_FILES, seal_run, verify_release


def _complete_run(root, *, split: str = "test") -> None:
    for name in RELEASE_FILES:
        path = root / name
        if name == "run-manifest.json":
            payload = {
                "run_id": "run_test",
                "split": split,
                "status": "scored",
                "api_key": "secret",
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
        else:
            payload = []
        if name.endswith(".jsonl"):
            path.write_text(json.dumps({"value": payload}) + "\n", encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")


def test_release_is_sanitized_closed_and_content_addressed(tmp_path) -> None:
    run_root = tmp_path / "run"
    release_root = tmp_path / "release"
    run_root.mkdir()
    _complete_run(run_root)
    manifest = seal_run(run_root=run_root, release_root=release_root)
    assert manifest == verify_release(release_root)
    released = json.loads((release_root / "run-manifest.json").read_text())
    assert released["api_key"] == "[REDACTED]"
    with pytest.raises(ValueError, match="empty"):
        seal_run(run_root=run_root, release_root=release_root)
    (release_root / "summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_release(release_root)


def test_incomplete_or_unadjudicated_run_cannot_be_sealed(tmp_path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    with pytest.raises(ValueError, match="missing"):
        seal_run(run_root=run_root, release_root=tmp_path / "release")


def test_validation_split_cannot_be_sealed(tmp_path) -> None:
    """The test split is not a tuning set; only it may ever be sealed."""

    run_root = tmp_path / "run"
    run_root.mkdir()
    _complete_run(run_root, split="validation")
    with pytest.raises(ValueError, match="test-split"):
        seal_run(run_root=run_root, release_root=tmp_path / "release")
