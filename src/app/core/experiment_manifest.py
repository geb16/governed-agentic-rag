from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pydantic import Field

from app.application.baseline.prompts import SYSTEM_PROMPT
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.version import (
    APP_VERSION,
    BASELINE_FREEZE_ID,
    DATABASE_SCHEMA_VERSION,
    TOOL_CONTRACT_VERSION,
)
from app.domain.schemas import StrictModel


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


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


def build_experiment_manifest(
    settings: Settings,
    tool_router: ToolRouter,
) -> ExperimentRunManifest:
    if settings.execution_profile != "experiment" or settings.experiment_run_id is None:
        raise ValueError("An experiment manifest can only be built for the experiment profile")
    knowledge_manifest = settings.knowledge_base_dir / "manifest.json"
    knowledge_manifest_sha256 = _sha256_bytes(knowledge_manifest.read_bytes())
    config_payload = {
        "freeze_id": BASELINE_FREEZE_ID,
        "model": settings.openai_model,
        "embedding_model": settings.openai_embedding_model,
        "retrieval_backend": settings.retrieval_backend,
        "qdrant_collection": settings.qdrant_collection,
        "knowledge_manifest_sha256": knowledge_manifest_sha256,
        "prompt_sha256": _sha256_bytes(SYSTEM_PROMPT.encode("utf-8")),
        "tool_schema_sha256": _canonical_sha256(tool_router.specs),
        "tool_contract_version": TOOL_CONTRACT_VERSION,
        "database_schema_version": DATABASE_SCHEMA_VERSION,
        "chunk_size_chars": settings.chunk_size_chars,
        "chunk_overlap_chars": settings.chunk_overlap_chars,
        "retrieval_top_k": settings.retrieval_top_k,
        "retrieval_min_score": settings.retrieval_min_score,
    }
    return ExperimentRunManifest(
        run_id=settings.experiment_run_id,
        created_at=datetime.now(UTC),
        app_version=APP_VERSION,
        package_versions={
            package: version(package)
            for package in ("fastapi", "openai", "pydantic", "qdrant-client")
        },
        configuration_sha256=_canonical_sha256(config_payload),
        **config_payload,
    )


# Record the experiment manifest to a file
def record_experiment_manifest(
    settings: Settings,
    tool_router: ToolRouter,
) -> tuple[ExperimentRunManifest, Path]:
    manifest = build_experiment_manifest(settings, tool_router)
    path = settings.experiment_manifest_dir / manifest.run_id / "manifest.json"

    def validate_existing() -> tuple[ExperimentRunManifest, Path]:
        existing = ExperimentRunManifest.model_validate_json(path.read_text(encoding="utf-8"))
        if existing.configuration_sha256 != manifest.configuration_sha256:
            raise RuntimeError(
                f"Experiment run {manifest.run_id} already exists with different configuration"
            )
        return existing, path

    if path.exists():
        return validate_existing()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as destination:
            destination.write(manifest.model_dump_json(indent=2))
    except FileExistsError:
        return validate_existing()
    return manifest, path
