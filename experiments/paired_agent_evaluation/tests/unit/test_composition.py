
from __future__ import annotations

import pytest
from app.evaluation.dataset.enums import DatasetSplit

import paired_agent_evaluation.composition as composition_module
from paired_agent_evaluation.composition import EvaluationPaths, prepare_run


class _StubSettings:
    """Stand in for the parts of ``app.core.config.Settings`` composition.py reads."""

    def __init__(self, *, openai_model: str = "gpt-5.6", **_: object) -> None:
        self.retrieval_backend = "qdrant"
        self.qdrant_collection = "phase3_enterprise_kb"
        self.openai_model = openai_model


@pytest.fixture
def isolated_paths(tmp_path) -> EvaluationPaths:
    """Real repository, config, and dataset; artifacts confined to ``tmp_path``."""

    real = EvaluationPaths.discover()
    return EvaluationPaths(
        repository=real.repository,
        project=real.project,
        artifacts=tmp_path / "artifacts",
        release=tmp_path / "release",
        configs=real.configs,
    )


@pytest.fixture(autouse=True)
def _stub_settings(monkeypatch, isolated_paths) -> None:
    monkeypatch.setattr(composition_module.EvaluationPaths, "discover", lambda: isolated_paths)
    monkeypatch.setattr(composition_module, "Settings", _StubSettings)


def test_prepare_run_is_idempotent_for_an_unchanged_repeat(isolated_paths) -> None:
    _, _, first, _ = prepare_run(run_id="run_composition_test", split=DatasetSplit.VALIDATION)
    _, _, second, _ = prepare_run(run_id="run_composition_test", split=DatasetSplit.VALIDATION)

    assert second == first


def test_prepare_run_rejects_drift_in_an_existing_run_manifest(monkeypatch, isolated_paths) -> None:
    prepare_run(run_id="run_composition_drift", split=DatasetSplit.VALIDATION)

    monkeypatch.setattr(
        composition_module,
        "Settings",
        lambda **kwargs: _StubSettings(openai_model="a-different-model", **kwargs),
    )

    with pytest.raises(ValueError, match="Existing run manifest drift"):
        prepare_run(run_id="run_composition_drift", split=DatasetSplit.VALIDATION)
