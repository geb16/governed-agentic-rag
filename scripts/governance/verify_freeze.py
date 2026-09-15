"""Write or verify the cryptographic identity of the Phase 4 governed treatment.

This verifier hashes the bounded Phase 4 release surface and derives one canonical
aggregate from its files and compatibility identities. It also pins the reviewed
Phase 3 v2 control manifest without duplicating ownership of the Phase 3 file scope.

Note: `--write` is used only after the complete release tree and verification suite have been
     reviewed; normal execution if this file is read-only and fails closed on drift.
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

from app.core.version import BASELINE_FREEZE_ID
from app.governance.stages.risk import GOVERNANCE_POLICY_VERSION
from app.governance.version import (
    BASELINE_CONTROL_SHA256,
    GOVERNED_APP_VERSION,
    WORKFLOW_SCHEMA_VERSION,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-4-governed" / "freeze-manifest.json"
PHASE3_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-3-baseline" / "freeze-manifest.json"
PHASE4_FREEZE_ID = "phase4-governance-v5"
MANIFEST_SCHEMA_VERSION = 1

# Phase 5 evaluation assets must remain outside this treatment identity.
FROZEN_PATTERNS = (
    ".env.example",
    "docs/phase-4-governed/dependency_composition_diagram.svg",
    "docs/phase-4-governed/architecture.md",
    "docs/phase-4-governed/README.md",
    "scripts/governance/run_smoke_tests.py",
    "scripts/governance/verify_freeze.py",
    "src/app/audit/*.py",
    "src/app/audit/**/*.py",
    "src/app/governance/*.py",
    "src/app/governance/**/*.py",
    "src/app/governed_main.py",
    "tests/governance/README.md",
    "tests/governance/*.py",
    "tests/governance/**/*.py",
)

IDENTITY_KEYS = (
    "manifest_schema_version",
    "freeze_id",
    "governed_app_version",
    "workflow_schema_version",
    "governance_policy_version",
    "baseline_freeze_id",
    "baseline_aggregate_sha256",
    "baseline_manifest_sha256",
)
COMPARABLE_KEYS = (*IDENTITY_KEYS, "source_files", "aggregate_sha256")
STORED_KEYS = frozenset((*COMPARABLE_KEYS, "frozen_at"))
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class FreezeScopeError(RuntimeError):
    """Raised when the Phase 4 scope or pinned Phase 3 identity is unsafe."""


def _sha256(value: bytes) -> str:
    """Return the lowercase SHA-256 digest for raw bytes."""
    return hashlib.sha256(value).hexdigest()


def _frozen_files() -> list[Path]:
    """Resolve every declared Phase 4 file and reject empty or symbolic-link scopes.

    Returns:
        Stable path-ordered files included in the Phase 4 identity.

    Raises:
        FreezeScopeError: If a pattern is empty or resolves to a symbolic link.
    """
    files: set[Path] = set()
    for pattern in FROZEN_PATTERNS:
        matches = {candidate for candidate in PROJECT_ROOT.glob(pattern) if candidate.is_file()}
        if not matches:
            raise FreezeScopeError(f"Frozen pattern matched no files: {pattern}")
        symlinks = sorted(candidate for candidate in matches if candidate.is_symlink())
        if symlinks:
            relative_paths = ", ".join(
                path.relative_to(PROJECT_ROOT).as_posix() for path in symlinks
            )
            raise FreezeScopeError(f"Frozen files must not be symbolic links: {relative_paths}")
        files.update(matches)
    return sorted(files, key=lambda path: path.relative_to(PROJECT_ROOT).as_posix())


def _phase3_identity() -> dict[str, str]:
    """Load and validate the exact Phase 3 control identity inherited by Phase 4.

    Returns:
        Baseline freeze ID, aggregate digest, and manifest-file digest.

    Raises:
        FreezeScopeError: If the manifest is unreadable, malformed, or not the
            reviewed Phase 3 v2 control referenced by governance code.
    """
    try:
        manifest_bytes = PHASE3_MANIFEST_PATH.read_bytes()
        payload = json.loads(manifest_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise FreezeScopeError(f"Phase 3 manifest cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise FreezeScopeError("Phase 3 manifest root must be an object")

    freeze_id = payload.get("freeze_id")
    aggregate = payload.get("aggregate_sha256")
    if freeze_id != BASELINE_FREEZE_ID:
        raise FreezeScopeError(
            f"Unexpected Phase 3 freeze identity: {freeze_id!r}; expected {BASELINE_FREEZE_ID!r}"
        )
    if aggregate != BASELINE_CONTROL_SHA256:
        raise FreezeScopeError("Phase 3 aggregate does not match the governed control identity")
    if not isinstance(aggregate, str) or _SHA256_PATTERN.fullmatch(aggregate) is None:
        raise FreezeScopeError("Phase 3 aggregate is not a lowercase SHA-256 digest")
    return {
        "baseline_freeze_id": freeze_id,
        "baseline_aggregate_sha256": aggregate,
        "baseline_manifest_sha256": _sha256(manifest_bytes),
    }


def _canonical_aggregate(payload: Mapping[str, Any]) -> str:
    """Derive the aggregate from every comparable field except the aggregate itself."""
    canonical = {key: payload[key] for key in COMPARABLE_KEYS if key != "aggregate_sha256"}
    encoded = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _sha256(encoded)


def build_freeze_payload() -> dict[str, Any]:
    """Hash the Phase 4 scope and bind it to release and baseline identities.

    Returns:
        Canonical payload without the non-comparable freeze timestamp.

    Raises:
        FreezeScopeError: If the Phase 4 scope or inherited Phase 3 identity is invalid.
    """
    hashes = {
        path.relative_to(PROJECT_ROOT).as_posix(): _sha256(path.read_bytes())
        for path in _frozen_files()
    }
    payload: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "freeze_id": PHASE4_FREEZE_ID,
        "governed_app_version": GOVERNED_APP_VERSION,
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "governance_policy_version": GOVERNANCE_POLICY_VERSION,
        **_phase3_identity(),
        "source_files": hashes,
    }
    payload["aggregate_sha256"] = _canonical_aggregate(payload)
    return payload


def _comparable_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Select stable manifest fields while excluding the review timestamp."""
    return {key: payload.get(key) for key in COMPARABLE_KEYS}


def _manifest_errors(payload: Mapping[str, Any]) -> list[str]:
    """Return deterministic structural and internal-integrity errors for a manifest."""
    errors: list[str] = []
    keys = set(payload)
    errors.extend(f"missing field: {key}" for key in sorted(STORED_KEYS - keys))
    errors.extend(f"unexpected field: {key}" for key in sorted(keys - STORED_KEYS))
    if errors:
        return errors

    if payload.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("manifest_schema_version is unsupported")
    if not isinstance(payload.get("frozen_at"), str):
        errors.append("frozen_at must be an ISO-8601 string")
    else:
        try:
            frozen_at = datetime.fromisoformat(payload["frozen_at"])
            if frozen_at.tzinfo is None:
                errors.append("frozen_at must include a timezone")
        except ValueError:
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

    for key in ("baseline_aggregate_sha256", "baseline_manifest_sha256", "aggregate_sha256"):
        value = payload.get(key)
        if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
            errors.append(f"{key} must be a lowercase SHA-256 digest")

    if not errors and payload["aggregate_sha256"] != _canonical_aggregate(payload):
        errors.append("aggregate_sha256 does not match the stored identity and source hashes")
    return errors


def _write_manifest(payload: Mapping[str, Any]) -> None:
    """Atomically write a reviewed payload with a UTC freeze timestamp."""
    stored_payload = {**payload, "frozen_at": datetime.now(UTC).isoformat()}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = MANIFEST_PATH.with_suffix(f"{MANIFEST_PATH.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(stored_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary_path.replace(MANIFEST_PATH)


def describe_freeze_differences(
    expected: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Return stable, reviewable diagnostics for Phase 4 identity drift."""
    differences: list[str] = []
    for key in IDENTITY_KEYS:
        if expected.get(key) != current.get(key):
            differences.append(f"{key} changed: {expected.get(key)!r} -> {current.get(key)!r}")

    expected_files = expected.get("source_files")
    current_files = current.get("source_files")
    if not isinstance(expected_files, dict):
        differences.append("stored source_files is missing or invalid")
    elif not isinstance(current_files, dict):
        differences.append("current source_files is missing or invalid")
    else:
        expected_paths = set(expected_files)
        current_paths = set(current_files)
        differences.extend(f"added: {path}" for path in sorted(current_paths - expected_paths))
        differences.extend(f"removed: {path}" for path in sorted(expected_paths - current_paths))
        differences.extend(
            f"modified: {path}"
            for path in sorted(expected_paths & current_paths)
            if expected_files[path] != current_files[path]
        )

    if not differences and expected.get("aggregate_sha256") != current.get("aggregate_sha256"):
        differences.append("aggregate_sha256 does not match the frozen Phase 4 identity")
    return differences


def main() -> int:
    """Write or verify the Phase 4 manifest selected by command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Write or verify the cryptographic Phase 4 governed-treatment manifest."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the named manifest after deliberate Phase 4 review.",
    )
    arguments = parser.parse_args()
    try:
        current = build_freeze_payload()
    except FreezeScopeError as error:
        print(f"Phase 4 freeze scope is invalid: {error}")
        return 1

    if arguments.write:
        _write_manifest(current)
        print(f"Wrote {PHASE4_FREEZE_ID}: {current['aggregate_sha256']}")
        return 0

    if not MANIFEST_PATH.exists():
        print(f"Freeze manifest is missing: {MANIFEST_PATH}")
        return 1
    try:
        expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Freeze manifest cannot be read: {error}")
        return 1
    if not isinstance(expected, dict):
        print("Freeze manifest is invalid: the root value must be an object.")
        return 1

    manifest_errors = _manifest_errors(expected)
    if manifest_errors:
        print("Freeze manifest is invalid:")
        for manifest_error in manifest_errors:
            print(f"- {manifest_error}")
        return 1

    comparable_expected = _comparable_payload(expected)
    if current != comparable_expected:
        print("Phase 4 freeze verification failed: frozen treatment files changed.")
        for difference in describe_freeze_differences(comparable_expected, current):
            print(f"- {difference}")
        return 1
    print(f"Verified {PHASE4_FREEZE_ID}: {current['aggregate_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
