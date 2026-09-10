# Capture non-secret runtime and infrastructure identities for each run.

from __future__ import annotations

from app.core.config import Settings

from paired_agent_evaluation.adapters.storage.filesystem import sha256_json
from paired_agent_evaluation.domain.executions import StrictModel
from paired_agent_evaluation.domain.manifests import Sha256

_RUNTIME_FIELDS = (
    "openai_model",
    "openai_embedding_model",
    "model_timeout_seconds",
    "model_max_retries",
    "model_max_output_tokens",
    "max_agent_turns",
    "max_tool_calls",
    "chunk_size_chars",
    "chunk_overlap_chars",
    "retrieval_top_k",
    "retrieval_min_score",
    "retrieval_backend",
    "qdrant_url",
    "qdrant_collection",
    "qdrant_timeout_seconds",
)


class RuntimeIdentity(StrictModel):
    """Content identities for runtime settings, tools, and vector data."""

    runtime_settings_sha256: Sha256
    tool_schema_sha256: Sha256
    qdrant_snapshot_sha256: Sha256
    qdrant_point_count: int


def _tool_schema_sha256() -> str:
    pass # TODO: Implement tool schema fingerprinting logic to compute SHA256 of tool schemas.

def _qdrant_snapshot(settings: Settings) -> tuple[str, int]:
    pass # TODO: Implement Qdrant snapshotting logic to compute SHA256 and point count.

# Fingerprint non-secret settings, tool schemas, and exact Qdrant records.
def capture_runtime_identity(settings: Settings) -> RuntimeIdentity:
    
    snapshot_sha256, point_count = _qdrant_snapshot(settings)
    runtime = {name: getattr(settings, name) for name in _RUNTIME_FIELDS}
    return RuntimeIdentity(
        runtime_settings_sha256=sha256_json(runtime),
        tool_schema_sha256=_tool_schema_sha256(),
        qdrant_snapshot_sha256=snapshot_sha256,
        qdrant_point_count=point_count,
    )
