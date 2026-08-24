"""Governed experiment-manifest identity and control-freeze verification tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.version import BASELINE_FREEZE_ID
from app.governance.experiments import manifest as manifest_module
from app.governance.version import BASELINE_CONTROL_SHA256
from app.tools.response_drafter import ResponseDrafterTool


def _write_control_manifest(
    directory: Path,
) -> tuple[Path, Path, dict[str, object], str]:
    """Write one internally consistent synthetic control manifest for verifier tests."""

    control_path = directory / "control.txt"
    control_path.write_text("reviewed", encoding="utf-8")
    source_files = {
        "control.txt": hashlib.sha256(control_path.read_bytes()).hexdigest(),
    }
    aggregate = hashlib.sha256(
        json.dumps(source_files, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    payload: dict[str, object] = {
        "manifest_schema_version": 1,
        "freeze_id": BASELINE_FREEZE_ID,
        "source_files": source_files,
        "aggregate_sha256": aggregate,
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    return control_path, manifest_path, payload, aggregate


def test_manifest_resolves_the_repository_root() -> None:
    """Prevent experiment startup from resolving assets below the ``src`` directory."""

    project_root = Path(__file__).resolve().parents[3]

    assert manifest_module._PROJECT_ROOT == project_root
    assert manifest_module._PHASE3_MANIFEST == (
        project_root / "docs" / "phase-3-freeze-manifest.json"
    )


def test_governed_control_identity_pins_the_reviewed_phase3_v2_manifest() -> None:
    """Prevent tests or runtime patching from masking a stale control identity."""

    payload = json.loads(manifest_module._PHASE3_MANIFEST.read_text(encoding="utf-8"))

    assert payload["freeze_id"] == BASELINE_FREEZE_ID == "phase3-baseline-v2"
    assert payload["aggregate_sha256"] == BASELINE_CONTROL_SHA256


def test_phase3_verifier_pins_manifest_and_file_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject both substituted manifest identities and changed control files."""

    control_path, manifest_path, manifest_payload, aggregate = _write_control_manifest(tmp_path)
    monkeypatch.setattr(manifest_module, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "_PHASE3_MANIFEST", manifest_path)
    monkeypatch.setattr(manifest_module, "BASELINE_CONTROL_SHA256", aggregate)

    assert manifest_module.verify_phase3_control_freeze() == aggregate

    manifest_path.write_text(
        json.dumps({**manifest_payload, "freeze_id": "substituted-baseline"}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="unexpected freeze identity"):
        manifest_module.verify_phase3_control_freeze()

    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    control_path.write_text("changed", encoding="utf-8")
    with pytest.raises(RuntimeError, match=r"changed files: control\.txt"):
        manifest_module.verify_phase3_control_freeze()


@pytest.mark.parametrize(
    ("manifest_change", "expected_error"),
    (
        ({"manifest_schema_version": 2}, "invalid or unsupported"),
        ({"source_files": {"control.txt": 7}}, "invalid source-file map"),
        ({"aggregate_sha256": "0" * 64}, "not the reviewed baseline"),
    ),
)
def test_phase3_verifier_rejects_invalid_manifest_structure_and_aggregate(
    manifest_change: dict[str, object],
    expected_error: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed on unsupported schemas, malformed maps, and substituted aggregates."""

    _, manifest_path, payload, aggregate = _write_control_manifest(tmp_path)
    manifest_path.write_text(
        json.dumps({**payload, **manifest_change}),
        encoding="utf-8",
    )
    monkeypatch.setattr(manifest_module, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(manifest_module, "_PHASE3_MANIFEST", manifest_path)
    monkeypatch.setattr(manifest_module, "BASELINE_CONTROL_SHA256", aggregate)

    with pytest.raises(RuntimeError, match=expected_error):
        manifest_module.verify_phase3_control_freeze()


def test_governed_manifest_records_reuses_and_rejects_configuration_drift(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep one experiment run immutable while allowing deterministic restart reuse."""

    settings = Settings(
        environment="test",
        execution_profile="experiment",
        openai_api_key=SecretStr("provider-test-key"),
        safety_identifier_secret=SecretStr("identity-test-secret"),
        retrieval_backend="qdrant",
        qdrant_url="https://qdrant.invalid",
        experiment_run_id="run_governed_manifest",
        experiment_manifest_dir=tmp_path,
        knowledge_base_dir=project_root / "data" / "knowledge_base",
    )
    router = ToolRouter([ResponseDrafterTool()])
    monkeypatch.setattr(
        manifest_module,
        "verify_phase3_control_freeze",
        lambda: BASELINE_CONTROL_SHA256,
    )

    created, path = manifest_module.record_governed_experiment_manifest(settings, router)
    reused, reused_path = manifest_module.record_governed_experiment_manifest(settings, router)

    assert path == reused_path
    assert created.configuration_sha256 == reused.configuration_sha256
    assert created.baseline_freeze_sha256 == BASELINE_CONTROL_SHA256
    assert created.condition == "governed"

    changed = settings.model_copy(update={"openai_model": "different-model"})
    with pytest.raises(RuntimeError, match="configuration drift"):
        manifest_module.record_governed_experiment_manifest(changed, router)

    with pytest.raises(RuntimeError, match="configuration drift"):
        manifest_module.record_governed_experiment_manifest(settings, ToolRouter([]))


def test_governed_manifest_requires_the_experiment_profile(settings: Settings) -> None:
    """Reject manifest creation outside the controlled experiment condition."""

    with pytest.raises(ValueError, match="experiment profile"):
        manifest_module.build_governed_experiment_manifest(
            settings,
            ToolRouter([ResponseDrafterTool()]),
        )
