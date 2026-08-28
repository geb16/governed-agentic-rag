# Deterministically render and verify the versioned Phase 5 artifacts.


from __future__ import annotations

import json
from typing import Any

from app.evaluation.dataset.generation.build import build_cases
from app.evaluation.dataset.generation.rubric import build_rubric
from app.evaluation.dataset.generation.sources import build_sources

_ARTIFACT_NAMES = (
    "cases.jsonl",
    "case.schema.json",
    "scoring-rubric.json",
    "rubric.schema.json",
    "sources.json",
)


def render_artifacts() -> dict[str, bytes]:
    """Render every content-addressed artifact without touching the filesystem."""
    cases = build_cases()
    rubric = build_rubric()
    payloads: dict[str, Any] = {
        "case.schema.json": cases[0].__class__.model_json_schema(),
        "scoring-rubric.json": rubric.model_dump(mode="json"),
        "rubric.schema.json": rubric.__class__.model_json_schema(),
        "sources.json": build_sources(),
    }
    rendered = {
        name: _json_bytes(payloads[name]) for name in _ARTIFACT_NAMES if name != "cases.jsonl"
    }
    rendered["cases.jsonl"] = b"".join(
        _compact_json_bytes(case.model_dump(mode="json")) for case in cases
    )
    return rendered


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _compact_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
