"""Phase 5 release-scope, ancestry, manifest, and drift-verifier tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.dataset.generation.artifacts import check_artifacts as real_check_artifacts
from app.evaluation.dataset.integrity import load_manifest as real_load_manifest
from app.evaluation.dataset.integrity import verify_manifest as real_verify_manifest
from scripts import verify_phase5_freeze as verifier

REAL_DATASET_ROOT = Path("data/evaluation/phase5/v1")


def _configure_isolated_scope(monkeypatch: pytest.MonkeyPatch, root: Path) -> Path:
    """Configure a minimal valid scope with both parent identities.

    Args:
        monkeypatch: Fixture used to isolate verifier dependencies.
        root: Temporary project root.

    Returns:
        Source file included in the isolated freeze scope.
    """
    source = root / "evaluation.py"
    source.write_text("RELEASE = 1\n", encoding="utf-8")
    phase3 = root / "phase3.json"
    phase3.write_text(
        json.dumps(
            {
                "freeze_id": verifier.PHASE3_FREEZE_ID,
                "aggregate_sha256": verifier.PHASE3_AGGREGATE_SHA256,
            }
        ),
        encoding="utf-8",
    )
    phase3_hash = verifier._sha256(phase3.read_bytes())
    phase4 = root / "phase4.json"
    phase4.write_text(
        json.dumps(
            {
                "freeze_id": verifier.PHASE4_FREEZE_ID,
                "aggregate_sha256": verifier.PHASE4_AGGREGATE_SHA256,
                "baseline_freeze_id": verifier.PHASE3_FREEZE_ID,
                "baseline_aggregate_sha256": verifier.PHASE3_AGGREGATE_SHA256,
                "baseline_manifest_sha256": phase3_hash,
            }
        ),
        encoding="utf-8",
    )
    dataset_manifest = root / "dataset.json"
    dataset_manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(verifier, "PROJECT_ROOT", root)
    monkeypatch.setattr(verifier, "MANIFEST_PATH", root / "phase5.json")
    monkeypatch.setattr(verifier, "PHASE3_MANIFEST_PATH", phase3)
    monkeypatch.setattr(verifier, "PHASE4_MANIFEST_PATH", phase4)
    monkeypatch.setattr(verifier, "DATASET_ROOT", root)
    monkeypatch.setattr(verifier, "DATASET_MANIFEST_PATH", dataset_manifest)
    monkeypatch.setattr(verifier, "FROZEN_PATTERNS", ("evaluation.py",))
    monkeypatch.setattr(verifier, "verify_manifest", lambda _: None)
    monkeypatch.setattr(verifier, "check_artifacts", lambda _: None)
    monkeypatch.setattr(
        verifier,
        "load_manifest",
        lambda _: SimpleNamespace(
            dataset_id="enterprise-support-agent-eval",
            dataset_version="1.0.0",
            case_count=100,
        ),
    )
    return source


def test_freeze_scope_covers_complete_phase5_release() -> None:
    """Freeze code, generation, tests, docs, data, and parent identities together."""
    payload = verifier.build_freeze_payload()
    source_files = payload["source_files"]

    assert isinstance(source_files, dict)
    assert {
        ".gitattributes",
        "data/evaluation/phase5/v1/cases.jsonl",
        "data/evaluation/phase5/v1/manifest.json",
        "docs/phase-5-evaluation/README.md",
        "docs/phase-5-evaluation/schema.md",
        "docs/phase-5-evaluation/scoring-rubric.md",
        "scripts/build_phase5_dataset.py",
        "scripts/verify_phase5_freeze.py",
        "src/app/evaluation/dataset/generation/artifacts.py",
        "src/app/evaluation/dataset/integrity.py",
        "src/app/evaluation/dataset/manifest.py",
        "tests/evaluation/dataset/test_integrity.py",
        "tests/evaluation/dataset/test_phase5_freeze_verifier.py",
    } <= source_files.keys()
    assert "docs/phase-5-evaluation/freeze-manifest.json" not in source_files
    assert all(not path.startswith("src/app/baseline/") for path in source_files)
    assert all(not path.startswith("src/app/governance/") for path in source_files)
    assert payload["baseline_aggregate_sha256"] == verifier.PHASE3_AGGREGATE_SHA256
    assert payload["governance_aggregate_sha256"] == verifier.PHASE4_AGGREGATE_SHA256
    assert payload["aggregate_sha256"] == verifier._canonical_aggregate(payload)


def test_freeze_rejects_stale_generated_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject a checked-in artifact that no longer matches its generator.

    A hand-edited artifact can still carry a self-consistent manifest hash, so
    ``verify_manifest`` alone would accept it. The freeze must also re-render
    every artifact and reject drift from the deterministic generator.

    Args:
        monkeypatch: Fixture used to isolate verifier dependencies.
        tmp_path: Pytest-managed isolation directory.
    """
    _configure_isolated_scope(monkeypatch, tmp_path)
    dataset_root = tmp_path / "dataset"
    shutil.copytree(REAL_DATASET_ROOT, dataset_root)

    sources_path = dataset_root / "sources.json"
    sources_payload = json.loads(sources_path.read_text(encoding="utf-8"))
    sources_payload["reviewed_on"] = "2099-01-01"
    mutated_sources = (json.dumps(sources_payload, indent=2, sort_keys=True) + "\n").encode()
    sources_path.write_bytes(mutated_sources)

    manifest_path = dataset_root / "manifest.json"
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_payload["files"]["sources.json"] = hashlib.sha256(mutated_sources).hexdigest()
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

    monkeypatch.setattr(verifier, "DATASET_ROOT", dataset_root)
    monkeypatch.setattr(verifier, "DATASET_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(verifier, "verify_manifest", real_verify_manifest)
    monkeypatch.setattr(verifier, "check_artifacts", real_check_artifacts)
    monkeypatch.setattr(verifier, "load_manifest", real_load_manifest)

    real_verify_manifest(dataset_root)  # manifest hashes are self-consistent despite the edit

    with pytest.raises(verifier.FreezeScopeError, match=r"sources\.json"):
        verifier.build_freeze_payload()


def test_line_ending_policy_is_lf_and_phase5_scoped() -> None:
    """Keep byte-hashed Phase 5 files portable without touching prior freezes."""
    policy_path = verifier.PROJECT_ROOT / ".gitattributes"
    rules = {
        line
        for raw_line in policy_path.read_text(encoding="utf-8").splitlines()
        if (line := raw_line.strip()) and not line.startswith("#")
    }

    required_phase5_rules = {
        "/data/evaluation/phase5/v1/*.json text eol=lf",
        "/data/evaluation/phase5/v1/*.jsonl text eol=lf",
        "/docs/phase-5-evaluation/*.md text eol=lf",
        "/docs/phase-5-evaluation/freeze-manifest.json text eol=lf",
        "/scripts/build_phase5_dataset.py text eol=lf",
        "/scripts/verify_phase5_freeze.py text eol=lf",
        "/src/app/evaluation/** text eol=lf",
        "/tests/evaluation/** text eol=lf",
    }

    assert "* text=auto eol=lf" in rules
    assert "/.gitattributes text eol=lf" in rules
    assert required_phase5_rules <= rules


def test_freeze_scope_rejects_empty_patterns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fail closed when a renamed path leaves the release scope.

    Args:
        monkeypatch: Fixture used to replace verifier paths and patterns.
        tmp_path: Pytest-managed isolation directory.
    """
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(verifier, "FROZEN_PATTERNS", ("missing/*.py",))

    with pytest.raises(verifier.FreezeScopeError, match="matched no files"):
        verifier._frozen_files()


def test_freeze_scope_rejects_broken_phase4_ancestry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject a Phase 4 manifest pinned to another control.

    Args:
        monkeypatch: Fixture used to isolate verifier dependencies.
        tmp_path: Pytest-managed isolation directory.
    """
    _configure_isolated_scope(monkeypatch, tmp_path)
    phase4 = json.loads(verifier.PHASE4_MANIFEST_PATH.read_text(encoding="utf-8"))
    phase4["baseline_manifest_sha256"] = "0" * 64
    verifier.PHASE4_MANIFEST_PATH.write_text(json.dumps(phase4), encoding="utf-8")

    with pytest.raises(verifier.FreezeScopeError, match="baseline manifest hash"):
        verifier.build_freeze_payload()


def test_stored_manifest_rejects_schema_source_and_aggregate_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reject stored schema, source-digest, and aggregate drift.

    Args:
        monkeypatch: Fixture used to isolate verifier dependencies.
        tmp_path: Pytest-managed isolation directory.
    """
    _configure_isolated_scope(monkeypatch, tmp_path)
    payload = {
        **verifier.build_freeze_payload(),
        "frozen_at": "2026-08-30T12:00:00+00:00",
    }
    assert verifier._manifest_errors(payload) == []

    payload["unexpected"] = True
    assert verifier._manifest_errors(payload) == ["unexpected field: unexpected"]
    payload.pop("unexpected")
    payload["source_files"] = {"evaluation.py": "invalid"}
    assert "source_files must map paths to lowercase SHA-256 digests" in verifier._manifest_errors(
        payload
    )


def test_cli_writes_verifies_and_reports_file_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify deliberate writes, read-only checks, and drift diagnostics.

    Args:
        monkeypatch: Fixture used to isolate CLI arguments and verifier dependencies.
        tmp_path: Pytest-managed isolation directory.
        capsys: Fixture capturing CLI diagnostics.
    """
    source = _configure_isolated_scope(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["verify_phase5_freeze.py", "--write"])
    assert verifier.main() == 0
    assert verifier.MANIFEST_PATH.is_file()

    monkeypatch.setattr(sys, "argv", ["verify_phase5_freeze.py"])
    assert verifier.main() == 0
    source.write_text("RELEASE = 2\n", encoding="utf-8")
    assert verifier.main() == 1
    assert "modified: evaluation.py" in capsys.readouterr().out
