# Deterministically render and verify the versioned Phase 5 artifacts.

# ruff: noqa: E501

from __future__ import annotations

import hashlib
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


def build_manifest(artifacts: dict[str, bytes]) -> bytes:
    """Build a stable manifest binding data to both frozen system versions."""
    manifest = {
        "manifest_schema_version": 1,
        "dataset_id": "enterprise-support-agent-eval",
        "dataset_version": "1.0.0",
        "distribution_type": "stratified_challenge_set_not_prevalence_sample",
        "released_at": "2026-08-25T00:00:00Z",
        "case_count": 100,
        "validation_case_count": 20,
        "test_case_count": 80,
        "baseline_freeze_id": "phase3-baseline-v2",
        "baseline_aggregate_sha256": "cd8c823a477419f7010c6d5beae1069baa154496e79fe52ed7fcaefcfe05f4b0",
        "governance_freeze_id": "phase4-governance-v1",
        "governance_aggregate_sha256": "a06eb798830e3cefea72978acc22d79dd6a2c51e53cf204ededffd8e7ceec46b",
        "files": {
            name: hashlib.sha256(content).hexdigest() for name, content in sorted(artifacts.items())
        },
    }
    return _json_bytes(manifest)

def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _compact_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
