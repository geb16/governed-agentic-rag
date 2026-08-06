from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.schemas import StrictModel


class ExperimentRunManifest(StrictModel):
    manifest_schema_version: int = 1
    freeze_id: str
    run_id: str
    created_at: datetime
    app_version: str
    model: str
    embedding_model: str
    retrieval_backend: str
    qdrant_collection: str
    knowledge_manifest_sha256: str
    prompt_sha256: str
    tool_schema_sha256: str
    tool_contract_version: int
    database_schema_version: int
    chunk_size_chars: int
    chunk_overlap_chars: int
    retrieval_top_k: int
    retrieval_min_score: float
    package_versions: dict[str, str]
    configuration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
