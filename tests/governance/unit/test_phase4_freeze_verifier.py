"""Phase 4 release-scope, manifest-integrity, and drift-verifier tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.core.version import BASELINE_FREEZE_ID
from app.governance.stages.risk import GOVERNANCE_POLICY_VERSION
from app.governance.version import (
    BASELINE_CONTROL_SHA256,
    GOVERNED_APP_VERSION,
    WORKFLOW_SCHEMA_VERSION,
)
from scripts import verify_phase4_freeze as verifier


def _configure_isolated_scope(monkeypatch: pytest.MonkeyPatch, directory: Path) -> Path:
    """Configure one-file Phase 4 and valid Phase 3 identities under a temporary root."""
    treatment_file = directory / "phase4.py"
    treatment_file.write_text("RELEASE = 1\n", encoding="utf-8")
    baseline_manifest = directory / "phase-3-freeze-manifest.json"
    baseline_manifest.write_text(
        json.dumps(
            {
                "freeze_id": BASELINE_FREEZE_ID,
                "aggregate_sha256": BASELINE_CONTROL_SHA256,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(verifier, "PROJECT_ROOT", directory)
    monkeypatch.setattr(verifier, "MANIFEST_PATH", directory / "phase-4-freeze-manifest.json")
    monkeypatch.setattr(verifier, "PHASE3_MANIFEST_PATH", baseline_manifest)
    monkeypatch.setattr(verifier, "FROZEN_PATTERNS", ("phase4.py",))
    return treatment_file


def test_freeze_scope_covers_phase4_release_and_excludes_phase5() -> None:
    """Keep the governed treatment complete without absorbing later evaluation assets."""
    payload = verifier.build_freeze_payload()
    source_files = payload["source_files"]

    assert isinstance(source_files, dict)
    assert {
        ".env.example",
        "docs/architecture/phase4_dependency_composition_diagram.svg",
        "docs/architecture/phase4_governance_architecture.md",
        "docs/phase-4-governance.md",
        "scripts/run_phase4_smoke_tests.py",
        "scripts/verify_phase4_freeze.py",
        "src/app/audit/sqlite/repository.py",
        "src/app/governance/composition.py",
        "src/app/governance/orchestration/workflow.py",
        "src/app/governance/stages/risk/policy.py",
        "src/app/governed_main.py",
        "tests/governance/README.md",
        "tests/governance/integration/test_workflow.py",
        "tests/governance/unit/test_phase4_freeze_verifier.py",
    } <= source_files.keys()
    assert "docs/phase-4-freeze-manifest.json" not in source_files
    assert "docs/phase-3-freeze-manifest.json" not in source_files
    assert all(not path.startswith("src/app/baseline/") for path in source_files)
    assert all(not path.startswith("tests/baseline/") for path in source_files)
    assert all(not path.startswith("tests/evaluation/") for path in source_files)
    assert all("__pycache__" not in path for path in source_files)


def test_freeze_payload_pins_release_schema_policy_and_baseline_identity() -> None:
    """Bind the treatment bytes to every compatibility identity used by experiments."""
    payload = verifier.build_freeze_payload()
    phase3_manifest = verifier.PHASE3_MANIFEST_PATH.read_bytes()

    assert payload["manifest_schema_version"] == verifier.MANIFEST_SCHEMA_VERSION == 1
    assert payload["freeze_id"] == verifier.PHASE4_FREEZE_ID == "phase4-governance-v2"
    assert payload["governed_app_version"] == GOVERNED_APP_VERSION
    assert payload["workflow_schema_version"] == WORKFLOW_SCHEMA_VERSION
    assert payload["governance_policy_version"] == GOVERNANCE_POLICY_VERSION
    assert payload["baseline_freeze_id"] == BASELINE_FREEZE_ID == "phase3-baseline-v3"
    assert payload["baseline_aggregate_sha256"] == BASELINE_CONTROL_SHA256
    assert payload["baseline_manifest_sha256"] == verifier._sha256(phase3_manifest)
    assert payload["aggregate_sha256"] == verifier._canonical_aggregate(payload)


def test_freeze_scope_rejects_a_pattern_that_matches_no_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fail closed when a renamed or removed release path escapes the declared scope."""
    monkeypatch.setattr(verifier, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(verifier, "FROZEN_PATTERNS", ("missing/*.py",))

    with pytest.raises(verifier.FreezeScopeError, match="matched no files"):
        verifier._frozen_files()


def test_freeze_scope_rejects_a_substituted_phase3_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Prevent Phase 4 from silently pointing at a different experimental control."""
    _configure_isolated_scope(monkeypatch, tmp_path)
    verifier.PHASE3_MANIFEST_PATH.write_text(
        json.dumps(
            {
                "freeze_id": "substituted-control",
                "aggregate_sha256": BASELINE_CONTROL_SHA256,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(verifier.FreezeScopeError, match="Unexpected Phase 3 freeze identity"):
        verifier.build_freeze_payload()


def test_manifest_validation_rejects_schema_source_map_and_aggregate_drift() -> None:
    """Reject malformed structure even before comparing it with current source bytes."""
    valid = {
        **verifier.build_freeze_payload(),
        "frozen_at": "2026-08-24T12:00:00+00:00",
    }
    assert verifier._manifest_errors(valid) == []

    invalid_schema = {**valid, "manifest_schema_version": 2}
    invalid_sources = {**valid, "source_files": {"unsafe.py": "not-a-digest"}}
    invalid_aggregate = {**valid, "aggregate_sha256": "0" * 64}

    assert "manifest_schema_version is unsupported" in verifier._manifest_errors(invalid_schema)
    assert "source_files must map paths" in verifier._manifest_errors(invalid_sources)[0]
    assert "aggregate_sha256 does not match" in verifier._manifest_errors(invalid_aggregate)[0]


def test_freeze_difference_diagnostics_identify_identity_and_file_changes() -> None:
    """Produce stable review output for added, removed, modified, and versioned drift."""
    expected = {key: "same" for key in verifier.IDENTITY_KEYS} | {
        "source_files": {"removed.py": "old", "modified.py": "old"},
        "aggregate_sha256": "old-aggregate",
    }
    current = {
        **expected,
        "governed_app_version": "changed",
        "source_files": {"added.py": "new", "modified.py": "new"},
        "aggregate_sha256": "new-aggregate",
    }

    assert verifier.describe_freeze_differences(expected, current) == [
        "governed_app_version changed: 'same' -> 'changed'",
        "added: added.py",
        "removed: removed.py",
        "modified: modified.py",
    ]


def test_cli_writes_verifies_and_detects_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exercise the operator workflow from atomic creation through drift failure."""
    treatment_file = _configure_isolated_scope(monkeypatch, tmp_path)

    monkeypatch.setattr(sys, "argv", ["verify_phase4_freeze.py", "--write"])
    assert verifier.main() == 0
    stored = json.loads(verifier.MANIFEST_PATH.read_text(encoding="utf-8"))
    assert set(stored) == verifier.STORED_KEYS
    assert stored["aggregate_sha256"] == verifier._canonical_aggregate(stored)

    monkeypatch.setattr(sys, "argv", ["verify_phase4_freeze.py"])
    assert verifier.main() == 0
    assert f"Verified {verifier.PHASE4_FREEZE_ID}" in capsys.readouterr().out

    treatment_file.write_text("RELEASE = 2\n", encoding="utf-8")
    assert verifier.main() == 1
    output = capsys.readouterr().out
    assert "Phase 4 freeze verification failed" in output
    assert "modified: phase4.py" in output
