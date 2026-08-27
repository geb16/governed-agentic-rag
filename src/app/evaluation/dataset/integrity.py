# Content-integrity helpers for immutable Phase 5 artifacts.

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of exact artifact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a manifest without weakening its explicit JSON boundary."""
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Dataset manifest must be a JSON object")
    return payload


def verify_manifest(root: Path) -> None:
    """Verify every declared artifact and reject undeclared missing files."""
    manifest = load_manifest(root / "manifest.json")
    files = manifest.get("files")
    if manifest.get("dataset_version") != "1.0.0" or not isinstance(files, dict):
        raise ValueError("Dataset manifest identity is invalid")
    for relative_path, expected_hash in files.items():
        candidate = (root / str(relative_path)).resolve(strict=True)
        if root.resolve() not in candidate.parents:
            raise ValueError("Dataset artifact escapes its version directory")
        if sha256_file(candidate) != expected_hash:
            raise ValueError(f"Dataset artifact integrity failed: {relative_path}")
