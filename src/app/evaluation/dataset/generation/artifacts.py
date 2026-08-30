# Deterministically render and verify the versioned Phase 5 artifacts.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.evaluation.dataset.generation.build import build_cases
from app.evaluation.dataset.generation.rubric import build_rubric
from app.evaluation.dataset.generation.sources import build_sources
from app.evaluation.dataset.manifest import (
    DATASET_ARTIFACT_NAMES,
    DATASET_RELEASE_NAMES,
    create_dataset_manifest,
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
        name: _json_bytes(payloads[name])
        for name in DATASET_ARTIFACT_NAMES
        if name != "cases.jsonl"
    }
    rendered["cases.jsonl"] = b"".join(
        _compact_json_bytes(case.model_dump(mode="json")) for case in cases
    )
    return rendered


def build_manifest(artifacts: dict[str, bytes]) -> bytes:
    """Build a stable manifest binding data to both frozen system versions."""
    manifest = create_dataset_manifest(
        {name: hashlib.sha256(content).hexdigest() for name, content in sorted(artifacts.items())}
    )
    return _json_bytes(manifest.model_dump(mode="json"))


def write_artifacts(root: Path) -> None:
    """Write a complete deterministic dataset release."""
    root.mkdir(parents=True, exist_ok=True)
    _reject_unexpected_entries(root)
    artifacts = render_artifacts()
    for name, content in artifacts.items():
        (root / name).write_bytes(content)
    (root / "manifest.json").write_bytes(build_manifest(artifacts))


def check_artifacts(root: Path) -> None:
    """Fail if checked-in artifacts differ from deterministic rendering."""
    _require_exact_release_entries(root)
    expected = render_artifacts()
    expected["manifest.json"] = build_manifest(expected)
    for name, content in expected.items():
        path = root / name
        if not path.is_file() or path.read_bytes() != content:
            raise ValueError(f"Generated Phase 5 artifact is stale: {path}")


def _reject_unexpected_entries(root: Path) -> None:
    """Refuse to overwrite a release directory containing undeclared entries."""
    unexpected = sorted(
        entry.name for entry in root.iterdir() if entry.name not in DATASET_RELEASE_NAMES
    )
    if unexpected:
        raise ValueError("Dataset release contains unexpected entries: " + ", ".join(unexpected))
    unsafe = sorted(entry.name for entry in root.iterdir() if entry.is_symlink())
    if unsafe:
        raise ValueError("Dataset release entries must not be symbolic links: " + ", ".join(unsafe))


def _require_exact_release_entries(root: Path) -> None:
    """Require the deterministic release to contain exactly the declared files."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Dataset release root must be a physical directory")
    names = {entry.name for entry in root.iterdir()}
    if names != DATASET_RELEASE_NAMES:
        missing = sorted(DATASET_RELEASE_NAMES - names)
        unexpected = sorted(names - DATASET_RELEASE_NAMES)
        details = [*(f"missing {name}" for name in missing)]
        details.extend(f"unexpected {name}" for name in unexpected)
        raise ValueError("Dataset release file set is invalid: " + ", ".join(details))
    _reject_unexpected_entries(root)


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _compact_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
