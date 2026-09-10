"""Captures content identities for an experiment's runtime dependencies.

Selected non-secret settings, registered tool schemas, and the complete Qdrant
collection are normalized and hashed. Persisting these identities with each run
makes later configuration or retrieval-data drift detectable.

References:
    [1] NIST, "Secure Hash Standard (SHS)," FIPS 180-4.
        https://doi.org/10.6028/NIST.FIPS.180-4
    [2] Qdrant, "Scroll points."
        https://api.qdrant.tech/api-reference/points/scroll-points
"""

from __future__ import annotations

from typing import Any

from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.tools.registry import build_shared_tools
from qdrant_client import QdrantClient

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
    """Records the inputs needed to detect runtime drift.

    Attributes:
        runtime_settings_sha256: Digest of selected non-secret settings.
        tool_schema_sha256: Digest of the tools exposed to the baseline agent.
        qdrant_snapshot_sha256: Digest of collection configuration and points.
        qdrant_point_count: Number of points included in the snapshot.
    """

    runtime_settings_sha256: Sha256
    tool_schema_sha256: Sha256
    qdrant_snapshot_sha256: Sha256
    qdrant_point_count: int


def _tool_schema_sha256() -> str:
    """Returns a stable digest of the registered tool specifications."""
    dependency: Any = object()
    specs = ToolRouter(build_shared_tools(dependency, dependency)).specs
    return sha256_json(specs)


def _qdrant_snapshot(settings: Settings) -> tuple[str, int]:
    """Hashes the configured Qdrant collection and all of its points.

    Pagination includes every point's identifier, payload, and vector. Points are
    sorted by identifier before hashing so the digest is independent of response
    page ordering. The client is closed whether collection access succeeds or
    fails.

    Args:
        settings: Qdrant connection and collection configuration.

    Returns:
        The collection snapshot digest and point count.

    Raises:
        ValueError: If the configured collection contains no points.
    """
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=(
            settings.qdrant_read_api_key.get_secret_value()
            if settings.qdrant_read_api_key is not None
            else None
        ),
        timeout=settings.qdrant_timeout_seconds,
    )
    points: list[dict[str, Any]] = []
    offset: Any = None
    try:
        configuration = client.get_collection(settings.qdrant_collection).config.params.model_dump(
            mode="json"
        )
        while True:
            records, offset = client.scroll(
                collection_name=settings.qdrant_collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            points.extend(
                record.model_dump(mode="json", include={"id", "payload", "vector"})
                if hasattr(record, "model_dump")
                else {"id": str(record.id), "payload": record.payload, "vector": record.vector}
                for record in records
            )
            if offset is None:
                break
    finally:
        client.close()
    if not points:
        raise ValueError("The experiment Qdrant collection is empty")
    points.sort(key=lambda point: str(point["id"]))
    snapshot = {
        "collection": settings.qdrant_collection,
        "configuration": configuration,
        "points": points,
    }
    return sha256_json(snapshot), len(points)


def capture_runtime_identity(settings: Settings) -> RuntimeIdentity:
    """Captures the reproducibility identity for the current runtime.

    Args:
        settings: Runtime configuration used for the experiment.

    Returns:
        Digests for selected settings, tool schemas, and Qdrant contents.
    """

    snapshot_sha256, point_count = _qdrant_snapshot(settings)
    runtime = {name: getattr(settings, name) for name in _RUNTIME_FIELDS}
    return RuntimeIdentity(
        runtime_settings_sha256=sha256_json(runtime),
        tool_schema_sha256=_tool_schema_sha256(),
        qdrant_snapshot_sha256=snapshot_sha256,
        qdrant_point_count=point_count,
    )
