# Content-integrity helpers for immutable Phase 5 artifacts.

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.loader import load_cases, load_rubric
from app.evaluation.dataset.manifest import (
    DATASET_ARTIFACT_NAMES,
    DATASET_RELEASE_NAMES,
    DatasetManifest,
)
from app.evaluation.dataset.validation import validate_dataset


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of exact artifact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> DatasetManifest:
    """Load and validate the complete, closed dataset-manifest contract."""
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Dataset manifest cannot be read: {error}") from error
    return DatasetManifest.model_validate(payload)


def verify_manifest(root: Path) -> None:
    """Verify exact membership, hashes, semantic counts, and inherited identities."""
    _verify_release_directory(root)
    manifest = load_manifest(root / "manifest.json")
    for relative_path in DATASET_ARTIFACT_NAMES:
        candidate = root / relative_path
        if sha256_file(candidate) != manifest.files[relative_path]:
            raise ValueError(f"Dataset artifact integrity failed: {relative_path}")

    cases = load_cases(root / "cases.jsonl")
    validate_dataset(cases)
    split_counts = Counter(case.split for case in cases)
    if (
        len(cases) != manifest.case_count
        or split_counts[DatasetSplit.VALIDATION] != manifest.validation_case_count
        or split_counts[DatasetSplit.TEST] != manifest.test_case_count
    ):
        raise ValueError("Dataset cases do not match manifest case and split counts")
    rubric = load_rubric(root / "scoring-rubric.json")
    if rubric.dataset_version != manifest.dataset_version:
        raise ValueError("Scoring rubric and dataset manifest versions differ")


def _verify_release_directory(root: Path) -> None:
    """Reject missing, extra, symbolic-link, and non-file release entries."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Dataset release root must be a physical directory")
    entries = {entry.name: entry for entry in root.iterdir()}
    actual_names = set(entries)
    if actual_names != DATASET_RELEASE_NAMES:
        missing = sorted(DATASET_RELEASE_NAMES - actual_names)
        unexpected = sorted(actual_names - DATASET_RELEASE_NAMES)
        details = [*(f"missing {name}" for name in missing)]
        details.extend(f"unexpected {name}" for name in unexpected)
        raise ValueError("Dataset release file set is invalid: " + ", ".join(details))
    unsafe = sorted(
        name for name, entry in entries.items() if entry.is_symlink() or not entry.is_file()
    )
    if unsafe:
        raise ValueError("Dataset release entries must be physical files: " + ", ".join(unsafe))
