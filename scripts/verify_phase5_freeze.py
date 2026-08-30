from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.evaluation.dataset.integrity import load_manifest, verify_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-5-freeze-manifest.json"
PHASE3_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-3-freeze-manifest.json"
PHASE4_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-4-freeze-manifest.json"
DATASET_ROOT = PROJECT_ROOT / "data" / "evaluation" / "phase5" / "v1"
DATASET_MANIFEST_PATH = DATASET_ROOT / "manifest.json"
PHASE5_FREEZE_ID = "phase5-evaluation-v1"
MANIFEST_SCHEMA_VERSION = 1

class FreezeScopeError(RuntimeError):
    """Raised when Phase 5 scope or inherited identities are unsafe."""


def _sha256(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact bytes."""
    return hashlib.sha256(value).hexdigest()


def _frozen_files() -> list[Path]:
    pass

def _parent_identity() -> dict[str, str]:
    pass

def _canonical_aggregate(payload: Mapping[str, Any]) -> str:
    pass
def build_freeze_payload() -> dict[str, Any]:
    """Build the complete Phase 5 identity after validating dataset semantics."""
    try:
        verify_manifest(DATASET_ROOT)
        dataset_manifest = load_manifest(DATASET_MANIFEST_PATH)
        dataset_manifest_bytes = DATASET_MANIFEST_PATH.read_bytes()
    except (OSError, ValueError) as error:
        raise FreezeScopeError(f"Dataset release is invalid: {error}") from error
    hashes = {
        path.relative_to(PROJECT_ROOT).as_posix(): _sha256(path.read_bytes())
        for path in _frozen_files()
    }
    payload: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "freeze_id": PHASE5_FREEZE_ID,
        "dataset_id": dataset_manifest.dataset_id,
        "dataset_version": dataset_manifest.dataset_version,
        "case_count": dataset_manifest.case_count,
        "dataset_manifest_sha256": _sha256(dataset_manifest_bytes),
        **_parent_identity(),
        "source_files": hashes,
    }
    payload["aggregate_sha256"] = _canonical_aggregate(payload)
    return payload
