from types import SimpleNamespace

from app.core.config import Settings

import paired_agent_evaluation.adapters.reproducibility as reproducibility


class _Qdrant:
    """Return the same records in deliberately noncanonical order."""

    def get_collection(self, _):
        params = SimpleNamespace(
            model_dump=lambda **_: {"vectors": {"size": 1, "distance": "Cosine"}}
        )
        return SimpleNamespace(config=SimpleNamespace(params=params))

    def scroll(self, **_):
        return (
            [
                SimpleNamespace(id=2, payload={"text": "second"}, vector=[0.2]),
                SimpleNamespace(id=1, payload={"text": "first"}, vector=[0.1]),
            ],
            None,
        )

    def close(self) -> None:
        pass


def test_runtime_identity_captures_settings_tools_and_exact_qdrant_content(monkeypatch) -> None:
    """Bind a run to non-secret settings, tool schemas, vectors, and payloads."""

    monkeypatch.setattr(reproducibility, "QdrantClient", lambda **_: _Qdrant())
    settings = Settings(retrieval_backend="qdrant", qdrant_url="http://qdrant.test")

    first = reproducibility.capture_runtime_identity(settings)
    second = reproducibility.capture_runtime_identity(settings)

    assert first == second
    assert first.qdrant_point_count == 2
    assert all(
        len(digest) == 64
        for digest in (
            first.runtime_settings_sha256,
            first.tool_schema_sha256,
            first.qdrant_snapshot_sha256,
        )
    )
