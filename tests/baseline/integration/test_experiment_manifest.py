"""Experiment-profile validation and immutable run-manifest contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.baseline import composition
from app.baseline.experiments import record_experiment_manifest
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.version import BASELINE_FREEZE_ID
from app.domain.evidence import RetrievedChunk
from app.tools.response_drafter import ResponseDrafterTool
from tests.baseline.support import ScriptedModel


class StubExperimentRetriever:
    """Offline retriever double for experiment-composition verification."""

    backend_name = "qdrant"
    chunk_count = 1

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return no chunks without contacting the configured vector service."""
        del query, top_k
        return []


def test_experiment_profile_requires_qdrant(project_root: Path, tmp_path: Path) -> None:
    """Reject an experiment profile that does not use the frozen Qdrant path."""
    with pytest.raises(ValidationError, match="requires RAG_RETRIEVAL_BACKEND=qdrant"):
        Settings(
            execution_profile="experiment",
            retrieval_backend="lexical",
            openai_api_key=SecretStr("test-key"),
            experiment_run_id="run_invalid_backend",
            knowledge_base_dir=project_root / "data" / "knowledge_base",
            synthetic_database_path=tmp_path / "state.db",
        )


def test_experiment_profile_records_and_reuses_frozen_run_manifest(
    project_root: Path,
    tmp_path: Path,
) -> None:
    """Reuse an identical named-run manifest without changing its identity."""
    settings = Settings(
        execution_profile="experiment",
        retrieval_backend="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        openai_api_key=SecretStr("test-key"),
        safety_identifier_secret=SecretStr("test-safety-secret"),
        experiment_run_id="run_manifest_test",
        experiment_manifest_dir=tmp_path / "runs",
        knowledge_base_dir=project_root / "data" / "knowledge_base",
        synthetic_database_path=tmp_path / "state.db",
    )
    router = ToolRouter([ResponseDrafterTool()])

    first, path = record_experiment_manifest(settings, router)
    second, second_path = record_experiment_manifest(settings, router)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == second_path
    assert first == second
    assert payload["freeze_id"] == BASELINE_FREEZE_ID
    assert payload["retrieval_backend"] == "qdrant"
    assert len(payload["configuration_sha256"]) == 64


def test_experiment_composition_records_and_exposes_manifest(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    tmp_path: Path,
) -> None:
    """Record experiment identity automatically while composing the runtime."""
    settings = Settings(
        environment="test",
        execution_profile="experiment",
        retrieval_backend="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        openai_api_key=SecretStr("test-key"),
        safety_identifier_secret=SecretStr("test-safety-secret"),
        experiment_run_id="run_automatic_manifest",
        experiment_manifest_dir=tmp_path / "runs",
        knowledge_base_dir=project_root / "data" / "knowledge_base",
        synthetic_database_path=tmp_path / "state.db",
    )
    monkeypatch.setattr(
        composition,
        "KnowledgeRetriever",
        lambda _settings: StubExperimentRetriever(),
    )
    monkeypatch.setattr(
        composition,
        "OpenAIResponsesModel",
        lambda _settings: ScriptedModel([]),
    )

    runtime = composition.build_runtime(settings)

    assert runtime.experiment_manifest is not None
    assert runtime.experiment_manifest.run_id == "run_automatic_manifest"
    assert (tmp_path / "runs" / "run_automatic_manifest" / "manifest.json").is_file()
