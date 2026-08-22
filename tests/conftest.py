"""Shared isolated settings, retrieval, and persistence fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.domain.support import DEFAULT_CASE_FIXTURE
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever


@pytest.fixture
def project_root() -> Path:
    """Return the repository root for tests that inspect project assets."""

    return Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(project_root: Path, tmp_path: Path) -> Settings:
    """Build governance-neutral settings with isolated persistent state."""

    return Settings(
        environment="test",
        execution_profile="test",
        api_key=None,
        openai_api_key=None,
        knowledge_base_dir=project_root / "data" / "knowledge_base",
        retrieval_backend="lexical",
        synthetic_database_path=tmp_path / "synthetic-support.db",
    )


@pytest.fixture
def retriever(settings: Settings) -> KnowledgeRetriever:
    """Create the shared deterministic lexical retriever."""

    return KnowledgeRetriever(settings)


@pytest.fixture
def repository(settings: Settings) -> SqliteSyntheticRepository:
    """Create case-isolated synthetic state for one test."""

    result = SqliteSyntheticRepository(settings.synthetic_database_path)
    result.initialize()
    result.create_case(DEFAULT_CASE_FIXTURE)
    return result
