from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


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

