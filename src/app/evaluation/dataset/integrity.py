"""Verify the closed, content-addressed Phase 5 dataset release.

Confirms a release directory contains exactly its declared physical files,
that every artifact's bytes match the manifest's SHA-256 digests, and that
the parsed cases and rubric satisfy their contracts.
Core:
    - sha256_file(): hashes exact artifact bytes.
    - load_manifest(): parses manifest.json through DatasetManifest.
    - verify_manifest(): end-to-end membership, hash, and count checks.
References:
    [1] NIST, "Secure Hash Standard," FIPS 180-4, 2015. https://doi.org/10.6028/NIST.FIPS.180-4
    [2] SLSA, "Build: Provenance," v1.0, 2023. https://slsa.dev/spec/v1.0/provenance
"""

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
    """Hash the exact bytes of an artifact.

    Args:
        path: Artifact to read.

    Returns:
        Lowercase SHA-256 digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> DatasetManifest:
    """Load a dataset manifest through its closed schema.

    Args:
        path: UTF-8 JSON manifest path.

    Returns:
        Validated dataset identity and artifact hashes.

    Raises:
        ValueError: If the file is unreadable, malformed, or violates the schema.
    """
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Dataset manifest cannot be read: {error}") from error
    return DatasetManifest.model_validate(payload)


def verify_manifest(root: Path) -> None:
    """Verify the complete dataset release against its manifest.

    Args:
        root: Version directory containing the manifest and artifacts.

    Raises:
        ValueError: If membership, hashes, counts, contracts, or identities differ.
    """
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
    """Require an exact set of physical files in a release directory.

    Args:
        root: Dataset version directory to inspect.

    Raises:
        ValueError: If the root or any release entry is missing, extra, or unsafe.
    """
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
