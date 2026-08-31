"""Create or verify the cryptographic identity of the Phase 5 release.

Normal execution is read-only and fails closed on release-scope, dataset, or inherited
identity drift. The ``--write`` path is reserved for a deliberately reviewed release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.evaluation.dataset.integrity import load_manifest, verify_manifest
from app.evaluation.dataset.manifest import (
    PHASE3_AGGREGATE_SHA256,
    PHASE3_FREEZE_ID,
    PHASE4_AGGREGATE_SHA256,
    PHASE4_FREEZE_ID,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-5-freeze-manifest.json"
PHASE3_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-3-freeze-manifest.json"
PHASE4_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-4-freeze-manifest.json"
DATASET_ROOT = PROJECT_ROOT / "data" / "evaluation" / "phase5" / "v1"
DATASET_MANIFEST_PATH = DATASET_ROOT / "manifest.json"
PHASE5_FREEZE_ID = "phase5-evaluation-v1"
MANIFEST_SCHEMA_VERSION = 1

FROZEN_PATTERNS = (
    ".gitattributes",
    "data/evaluation/phase5/v1/case.schema.json",
    "data/evaluation/phase5/v1/cases.jsonl",
    "data/evaluation/phase5/v1/manifest.json",
    "data/evaluation/phase5/v1/rubric.schema.json",
    "data/evaluation/phase5/v1/scoring-rubric.json",
    "data/evaluation/phase5/v1/sources.json",
    "docs/phase-5-evaluation/*.md",
    "scripts/build_phase5_dataset.py",
    "scripts/verify_phase5_freeze.py",
    "src/app/evaluation/*.py",
    "src/app/evaluation/**/*.py",
    "tests/evaluation/*.py",
    "tests/evaluation/**/*.py",
)
IDENTITY_KEYS = (
    "manifest_schema_version",
    "freeze_id",
    "dataset_id",
    "dataset_version",
    "case_count",
    "dataset_manifest_sha256",
    "baseline_freeze_id",
    "baseline_aggregate_sha256",
    "baseline_manifest_sha256",
    "governance_freeze_id",
    "governance_aggregate_sha256",
    "governance_manifest_sha256",
)

COMPARABLE_KEYS = (*IDENTITY_KEYS, "source_files", "aggregate_sha256")
STORED_KEYS = frozenset((*COMPARABLE_KEYS, "frozen_at"))
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class FreezeScopeError(RuntimeError):
    """Raised when Phase 5 scope or inherited identities are unsafe."""


def _sha256(value: bytes) -> str:
    """Hash exact bytes with SHA-256.

    Args:
        value: Bytes to hash without normalization.

    Returns:
        Lowercase hexadecimal digest.
    """
    return hashlib.sha256(value).hexdigest()


def _frozen_files() -> list[Path]:
    """Resolve the declared Phase 5 release scope.

    Returns:
        Physical files ordered by project-relative POSIX path.

    Raises:
        FreezeScopeError: If a pattern is empty or includes a symbolic link.
    """
    files: set[Path] = set()
    for pattern in FROZEN_PATTERNS:
        matches = {candidate for candidate in PROJECT_ROOT.glob(pattern) if candidate.is_file()}
        if not matches:
            raise FreezeScopeError(f"Frozen pattern matched no files: {pattern}")
        symlinks = sorted(candidate for candidate in matches if candidate.is_symlink())
        if symlinks:
            paths = ", ".join(path.relative_to(PROJECT_ROOT).as_posix() for path in symlinks)
            raise FreezeScopeError(f"Frozen files must not be symbolic links: {paths}")
        files.update(matches)
    return sorted(files, key=lambda path: path.relative_to(PROJECT_ROOT).as_posix())


def _read_manifest(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    """Read a parent manifest while preserving its exact bytes.

    Args:
        path: Manifest JSON path.
        label: Release label used in diagnostics.

    Returns:
        Parsed object and the original file bytes.

    Raises:
        FreezeScopeError: If the manifest is unreadable, malformed, or not an object.
    """
    try:
        content = path.read_bytes()
        payload: Any = json.loads(content)
    except (OSError, json.JSONDecodeError) as error:
        raise FreezeScopeError(f"{label} manifest cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise FreezeScopeError(f"{label} manifest root must be an object")
    return payload, content


def _parent_identity() -> dict[str, str]:
    """Validate the Phase 3 and Phase 4 release ancestry.

    Returns:
        Parent freeze IDs, aggregate hashes, and manifest hashes.

    Raises:
        FreezeScopeError: If an identity, ancestry link, or digest is invalid.
    """
    phase3, phase3_bytes = _read_manifest(PHASE3_MANIFEST_PATH, "Phase 3")
    phase4, phase4_bytes = _read_manifest(PHASE4_MANIFEST_PATH, "Phase 4")
    phase3_manifest_hash = _sha256(phase3_bytes)
    expected_values = (
        (phase3.get("freeze_id"), PHASE3_FREEZE_ID, "Phase 3 freeze ID"),
        (phase3.get("aggregate_sha256"), PHASE3_AGGREGATE_SHA256, "Phase 3 aggregate"),
        (phase4.get("freeze_id"), PHASE4_FREEZE_ID, "Phase 4 freeze ID"),
        (phase4.get("aggregate_sha256"), PHASE4_AGGREGATE_SHA256, "Phase 4 aggregate"),
        (phase4.get("baseline_freeze_id"), PHASE3_FREEZE_ID, "Phase 4 baseline freeze ID"),
        (
            phase4.get("baseline_aggregate_sha256"),
            PHASE3_AGGREGATE_SHA256,
            "Phase 4 baseline aggregate",
        ),
        (
            phase4.get("baseline_manifest_sha256"),
            phase3_manifest_hash,
            "Phase 4 baseline manifest hash",
        ),
    )
    for actual, expected, label in expected_values:
        if actual != expected:
            raise FreezeScopeError(f"{label} does not match the reviewed release")
    for value, _, label in expected_values:
        if "ID" not in label and (
            not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None
        ):
            raise FreezeScopeError(f"{label} is not a lowercase SHA-256 digest")
    return {
        "baseline_freeze_id": PHASE3_FREEZE_ID,
        "baseline_aggregate_sha256": PHASE3_AGGREGATE_SHA256,
        "baseline_manifest_sha256": phase3_manifest_hash,
        "governance_freeze_id": PHASE4_FREEZE_ID,
        "governance_aggregate_sha256": PHASE4_AGGREGATE_SHA256,
        "governance_manifest_sha256": _sha256(phase4_bytes),
    }


def _canonical_aggregate(payload: Mapping[str, Any]) -> str:
    """Derive an aggregate from all stable comparable fields.

    Args:
        payload: Freeze identity and source-file hashes.

    Returns:
        SHA-256 digest of the canonical JSON representation.
    """
    canonical = {key: payload[key] for key in COMPARABLE_KEYS if key != "aggregate_sha256"}
    encoded = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    return _sha256(encoded)


def build_freeze_payload() -> dict[str, Any]:
    """Build the complete Phase 5 release identity.

    Returns:
        Comparable identities and per-file hashes with their aggregate.

    Raises:
        FreezeScopeError: If the dataset, scope, or inherited releases are invalid.
    """
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


def _manifest_errors(payload: Mapping[str, Any]) -> list[str]:
    """Validate a stored freeze manifest without reading release files.

    Args:
        payload: Parsed stored manifest.

    Returns:
        Stable structural and internal-integrity diagnostics.
    """
    errors: list[str] = []
    keys = set(payload)
    errors.extend(f"missing field: {key}" for key in sorted(STORED_KEYS - keys))
    errors.extend(f"unexpected field: {key}" for key in sorted(keys - STORED_KEYS))
    if errors:
        return errors
    if payload.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("manifest_schema_version is unsupported")
    try:
        timestamp = datetime.fromisoformat(payload["frozen_at"])
        if timestamp.tzinfo is None:
            errors.append("frozen_at must include a timezone")
    except (TypeError, ValueError):
        errors.append("frozen_at must be an ISO-8601 string")
    source_files = payload.get("source_files")
    if not isinstance(source_files, dict) or not source_files:
        errors.append("source_files must be a non-empty object")
    elif any(
        not isinstance(path, str)
        or not isinstance(digest, str)
        or _SHA256_PATTERN.fullmatch(digest) is None
        for path, digest in source_files.items()
    ):
        errors.append("source_files must map paths to lowercase SHA-256 digests")
    for key in (
        "dataset_manifest_sha256",
        "baseline_aggregate_sha256",
        "baseline_manifest_sha256",
        "governance_aggregate_sha256",
        "governance_manifest_sha256",
        "aggregate_sha256",
    ):
        value = payload.get(key)
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            errors.append(f"{key} must be a lowercase SHA-256 digest")
    if not errors and payload["aggregate_sha256"] != _canonical_aggregate(payload):
        errors.append("aggregate_sha256 does not match the stored identity and source hashes")
    return errors


def _write_manifest(payload: Mapping[str, Any]) -> None:
    """Atomically persist a reviewed payload with a UTC timestamp.

    Args:
        payload: Valid comparable freeze payload.
    """
    stored = {**payload, "frozen_at": datetime.now(UTC).isoformat()}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(f"{MANIFEST_PATH.suffix}.tmp")
    temporary.write_text(
        json.dumps(stored, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(MANIFEST_PATH)


def describe_freeze_differences(
    expected: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Describe identity and file drift in stable order.

    Args:
        expected: Comparable fields from the stored manifest.
        current: Comparable fields computed from the workspace.

    Returns:
        Human-readable added, removed, modified, and identity differences.
    """
    differences = [
        f"{key} changed: {expected.get(key)!r} -> {current.get(key)!r}"
        for key in IDENTITY_KEYS
        if expected.get(key) != current.get(key)
    ]
    expected_files = expected.get("source_files")
    current_files = current.get("source_files")
    if not isinstance(expected_files, dict) or not isinstance(current_files, dict):
        return [*differences, "source_files is missing or invalid"]
    expected_paths, current_paths = set(expected_files), set(current_files)
    differences.extend(f"added: {path}" for path in sorted(current_paths - expected_paths))
    differences.extend(f"removed: {path}" for path in sorted(expected_paths - current_paths))
    differences.extend(
        f"modified: {path}"
        for path in sorted(expected_paths & current_paths)
        if expected_files[path] != current_files[path]
    )
    if not differences and expected.get("aggregate_sha256") != current.get("aggregate_sha256"):
        differences.append("aggregate_sha256 does not match the frozen Phase 5 identity")
    return differences


def main() -> int:
    """Run the selected write or read-only verification command.

    Returns:
        Process exit code: zero on success, otherwise one.
    """
    parser = argparse.ArgumentParser(description="Write or verify the Phase 5 release manifest.")
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    try:
        current = build_freeze_payload()
    except FreezeScopeError as error:
        print(f"Phase 5 freeze scope is invalid: {error}")
        return 1
    if arguments.write:
        _write_manifest(current)
        print(f"Wrote {PHASE5_FREEZE_ID}: {current['aggregate_sha256']}")
        return 0
    if not MANIFEST_PATH.exists():
        print(f"Freeze manifest is missing: {MANIFEST_PATH}")
        return 1
    try:
        expected: Any = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Freeze manifest cannot be read: {error}")
        return 1
    if not isinstance(expected, dict):
        print("Freeze manifest is invalid: the root value must be an object.")
        return 1
    errors = _manifest_errors(expected)
    if errors:
        print("Freeze manifest is invalid:")
        for manifest_error in errors:
            print(f"- {manifest_error}")
        return 1
    comparable = {key: expected.get(key) for key in COMPARABLE_KEYS}
    if current != comparable:
        print("Phase 5 freeze verification failed: frozen evaluation files changed.")
        for difference in describe_freeze_differences(comparable, current):
            print(f"- {difference}")
        return 1
    print(f"Verified {PHASE5_FREEZE_ID}: {current['aggregate_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
