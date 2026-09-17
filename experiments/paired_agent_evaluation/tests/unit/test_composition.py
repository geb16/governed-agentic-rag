"""Verify composition builds reproducible runs and enforces execution gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.evaluation.dataset.enums import DatasetSplit

import paired_agent_evaluation.composition.builder as composition_builder
from paired_agent_evaluation.adapters.reproducibility import RuntimeIdentity
from paired_agent_evaluation.composition import EvaluationPaths, acquire, prepare_run


class _StubSettings:
    """Provide the settings subset consumed by the composition builder."""

    def __init__(
        self,
        *,
        openai_model: str = "gpt-5.6",
        knowledge_base_dir: Path,
        **_: object,
    ) -> None:
        self.retrieval_backend = "qdrant"
        self.qdrant_collection = "phase3_enterprise_kb"
        self.openai_model = openai_model
        self.knowledge_base_dir = knowledge_base_dir


@pytest.fixture
def isolated_paths(tmp_path: Path) -> EvaluationPaths:
    """Use real inputs while confining generated artifacts to a temporary root."""

    real = EvaluationPaths.discover()
    return EvaluationPaths(
        repository=real.repository,
        project=real.project,
        artifacts=tmp_path / "artifacts",
        release=tmp_path / "release",
        configs=real.configs,
    )


@pytest.fixture(autouse=True)
def _stub_settings(
    monkeypatch: pytest.MonkeyPatch,
    isolated_paths: EvaluationPaths,
) -> None:
    """Isolate external runtime identity and settings dependencies."""
    monkeypatch.setattr(EvaluationPaths, "discover", lambda: isolated_paths)
    monkeypatch.setattr(composition_builder, "Settings", _StubSettings)
    monkeypatch.setattr(
        composition_builder,
        "capture_runtime_identity",
        lambda _: RuntimeIdentity(
            runtime_settings_sha256="a" * 64,
            tool_schema_sha256="b" * 64,
            qdrant_snapshot_sha256="c" * 64,
            qdrant_point_count=1,
        ),
    )


def test_prepare_run_is_idempotent_for_an_unchanged_repeat(
    isolated_paths: EvaluationPaths,
) -> None:
    """Reuse an unchanged run without regenerating its private blinding plan."""
    _, _, first, _ = prepare_run(run_id="run_composition_test", split=DatasetSplit.VALIDATION)
    plan_path = isolated_paths.run_root("run_composition_test") / "blinding-plan.json"
    original_plan = plan_path.read_bytes()
    _, _, second, _ = prepare_run(run_id="run_composition_test", split=DatasetSplit.VALIDATION)

    assert second == first
    assert plan_path.read_bytes() == original_plan


def test_prepare_run_binds_the_frozen_knowledge_base(
    isolated_paths: EvaluationPaths,
) -> None:
    """Resolve experiment retrieval data independently of the working directory."""
    _, _, _, settings = prepare_run(
        run_id="run_knowledge_base_path",
        split=DatasetSplit.VALIDATION,
    )

    expected = isolated_paths.repository / "data" / "knowledge_base"
    assert settings.knowledge_base_dir == expected
    assert settings.knowledge_base_dir.is_absolute()


def test_prepare_run_rejects_blinding_plan_drift(isolated_paths: EvaluationPaths) -> None:
    """Reject reuse when persisted blinding assignments no longer match."""
    prepare_run(run_id="run_blinding_drift", split=DatasetSplit.VALIDATION)
    plan_path = isolated_paths.run_root("run_blinding_drift") / "blinding-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    first_observation = next(iter(plan["assignments"]))
    plan["assignments"][first_observation] = f"blind_{'f' * 32}"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest drift"):
        prepare_run(run_id="run_blinding_drift", split=DatasetSplit.VALIDATION)


def test_prepare_run_rejects_drift_in_an_existing_run_manifest(
    monkeypatch: pytest.MonkeyPatch,
    isolated_paths: EvaluationPaths,
) -> None:
    """Reject reuse when current configuration differs from the run manifest."""
    prepare_run(run_id="run_composition_drift", split=DatasetSplit.VALIDATION)

    monkeypatch.setattr(
        composition_builder,
        "Settings",
        lambda **kwargs: _StubSettings(openai_model="a-different-model", **kwargs),
    )

    with pytest.raises(ValueError, match="Existing run manifest drift"):
        prepare_run(run_id="run_composition_drift", split=DatasetSplit.VALIDATION)


def test_prepare_run_rejects_runtime_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent reuse after settings, tool schemas, or Qdrant content changes."""

    prepare_run(run_id="run_runtime_drift", split=DatasetSplit.VALIDATION)
    monkeypatch.setattr(
        composition_builder,
        "capture_runtime_identity",
        lambda _: RuntimeIdentity(
            runtime_settings_sha256="9" * 64,
            tool_schema_sha256="b" * 64,
            qdrant_snapshot_sha256="c" * 64,
            qdrant_point_count=1,
        ),
    )

    with pytest.raises(ValueError, match="runtime_settings_sha256"):
        prepare_run(run_id="run_runtime_drift", split=DatasetSplit.VALIDATION)


def test_generic_acquisition_cannot_bypass_the_test_execution_gate() -> None:
    """Require the preregistered one-time path for test-split acquisition."""
    with pytest.raises(ValueError, match="preregistered one-time execution gate"):
        acquire(run_id="run_unregistered_test", split=DatasetSplit.TEST)
