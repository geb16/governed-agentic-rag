"""Phase 5 release-scope, ancestry, manifest, and drift-verifier tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_phase5_freeze as verifier


def _configure_isolated_scope(monkeypatch: pytest.MonkeyPatch, root: Path) -> Path:
    """Create a minimal valid verifier scope with both parent identities."""
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
    """Freeze code, generator, tests, docs, data, and inherited identities together."""
    payload = verifier.build_freeze_payload()
    source_files = payload["source_files"]

    assert isinstance(source_files, dict)
    assert {
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
    assert "docs/phase-5-freeze-manifest.json" not in source_files
    assert all(not path.startswith("src/app/baseline/") for path in source_files)
    assert all(not path.startswith("src/app/governance/") for path in source_files)
    assert payload["baseline_aggregate_sha256"] == verifier.PHASE3_AGGREGATE_SHA256
    assert payload["governance_aggregate_sha256"] == verifier.PHASE4_AGGREGATE_SHA256
    assert payload["aggregate_sha256"] == verifier._canonical_aggregate(payload)


def test_freeze_scope_rejects_empty_patterns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fail closed when a renamed path silently leaves the declared release scope."""
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(verifier, "FROZEN_PATTERNS", ("missing/*.py",))

    with pytest.raises(verifier.FreezeScopeError, match="matched no files"):
        verifier._frozen_files()


def test_freeze_scope_rejects_broken_phase4_ancestry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Prevent Phase 5 from accepting a Phase 4 manifest pinned to another control."""
    _configure_isolated_scope(monkeypatch, tmp_path)
    phase4 = json.loads(verifier.PHASE4_MANIFEST_PATH.read_text(encoding="utf-8"))
    phase4["baseline_manifest_sha256"] = "0" * 64
    verifier.PHASE4_MANIFEST_PATH.write_text(json.dumps(phase4), encoding="utf-8")

    with pytest.raises(verifier.FreezeScopeError, match="baseline manifest hash"):
        verifier.build_freeze_payload()

