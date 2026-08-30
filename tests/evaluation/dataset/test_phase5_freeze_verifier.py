"""Phase 5 release-scope, ancestry, manifest, and drift-verifier tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import verify_phase5_freeze as verifier


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
