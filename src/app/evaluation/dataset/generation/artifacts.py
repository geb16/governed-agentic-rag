"""Render and verify deterministic, versioned Phase 5 artifacts.

Serializes cases, rubric, schemas, and sources to stable, sorted-key JSON
(and compact JSONL) bytes, then binds them to a manifest. check_artifacts()
re-renders in memory and compares bytes so a stale file fails closed
instead of silently diverging from the generator.
Core:
    - render_artifacts(), build_manifest(): deterministic byte rendering.
    - write_artifacts(): writes a fresh release to disk.
    - check_artifacts(): rejects drift from deterministic regeneration.
References:
    [1] Rundgren et al., "JCS," RFC 8785, IETF, 2020. https://doi.org/10.17487/RFC8785
    [2] NIST, "Secure Hash Standard," FIPS 180-4, 2015. https://doi.org/10.6028/NIST.FIPS.180-4
"""

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
    """Render every content-addressed artifact in memory.

    Returns:
        Relative artifact names mapped to deterministic bytes.
    """
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
    """Render a manifest binding artifacts to both frozen systems.

    Args:
        artifacts: Release artifact names mapped to exact bytes.

    Returns:
        Deterministic UTF-8 JSON manifest bytes.

    Raises:
        ValueError: If artifact membership violates the manifest contract.
    """
    manifest = create_dataset_manifest(
        {name: hashlib.sha256(content).hexdigest() for name, content in sorted(artifacts.items())}
    )
    return _json_bytes(manifest.model_dump(mode="json"))


def write_artifacts(root: Path) -> None:
    """Write a complete deterministic dataset release.

    Args:
        root: Version directory to create or update.

    Raises:
        ValueError: If the directory contains undeclared or symbolic-link entries.
    """
    root.mkdir(parents=True, exist_ok=True)
    _reject_unexpected_entries(root)
    artifacts = render_artifacts()
    for name, content in artifacts.items():
        (root / name).write_bytes(content)
    (root / "manifest.json").write_bytes(build_manifest(artifacts))


def check_artifacts(root: Path) -> None:
    """Compare checked-in artifacts with deterministic rendering.

    Args:
        root: Existing dataset version directory.

    Raises:
        ValueError: If membership or any artifact byte differs.
    """
    _require_exact_release_entries(root)
    expected = render_artifacts()
    expected["manifest.json"] = build_manifest(expected)
    for name, content in expected.items():
        path = root / name
        if not path.is_file() or path.read_bytes() != content:
            raise ValueError(f"Generated Phase 5 artifact is stale: {path}")


def _reject_unexpected_entries(root: Path) -> None:
    """Reject undeclared or symbolic-link entries before writing.

    Args:
        root: Dataset version directory to inspect.

    Raises:
        ValueError: If an entry is undeclared or symbolic.
    """
    unexpected = sorted(
        entry.name for entry in root.iterdir() if entry.name not in DATASET_RELEASE_NAMES
    )
    if unexpected:
        raise ValueError("Dataset release contains unexpected entries: " + ", ".join(unexpected))
    unsafe = sorted(entry.name for entry in root.iterdir() if entry.is_symlink())
    if unsafe:
        raise ValueError("Dataset release entries must not be symbolic links: " + ", ".join(unsafe))


def _require_exact_release_entries(root: Path) -> None:
    """Require exactly the declared physical release files.

    Args:
        root: Dataset version directory to inspect.

    Raises:
        ValueError: If the directory or its membership is invalid.
    """
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
    """Serialize a value as stable, indented UTF-8 JSON bytes.

    Args:
        payload: JSON-compatible value to serialize.

    Returns:
        Sorted JSON terminated by one newline.
    """
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def _compact_json_bytes(payload: Any) -> bytes:
    """Serialize a value as stable, compact UTF-8 JSON Lines bytes.

    Args:
        payload: JSON-compatible value to serialize.

    Returns:
        Compact sorted JSON terminated by one newline.
    """
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
