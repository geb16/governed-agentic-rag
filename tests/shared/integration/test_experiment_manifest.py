from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.experiment_manifest import record_experiment_manifest
from app.core.version import BASELINE_FREEZE_ID
from app.tools.response_drafter import ResponseDrafterTool


# Check that the experiment profile requires the retrieval backend to be qdrant.
def test_experiment_profile_requires_qdrant(project_root: Path, tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="requires RAG_RETRIEVAL_BACKEND=qdrant"):
        Settings(
            execution_profile="experiment",
            retrieval_backend="lexical",
            openai_api_key=SecretStr("test-key"),
            experiment_run_id="run_invalid_backend",
            knowledge_base_dir=project_root / "data" / "knowledge_base",
            synthetic_database_path=tmp_path / "state.db",
        )


# Testing that the experiment profile correctly records and reuses a frozen run manifest
def test_experiment_profile_records_and_reuses_frozen_run_manifest(
    project_root: Path,
    tmp_path: Path,
) -> None:
    settings = Settings(
        execution_profile="experiment",
        retrieval_backend="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        openai_api_key=SecretStr("test-key"),
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
