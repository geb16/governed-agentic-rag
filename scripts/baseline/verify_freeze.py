"""Write or verify the cryptographic identity of the Phase 3 baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.version import APP_VERSION, BASELINE_FREEZE_ID

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-3-baseline" / "freeze-manifest.json"

# Phase 4 governance tests must not alter the Phase 3 identity.
FROZEN_PATTERNS = (
    "docker-compose.yml",
    "pyproject.toml",
    "uv.lock",
    "data/knowledge_base/*",
    "docs/phase-3-baseline/architecture.md",
    "docs/phase-3-baseline/README.md",
    "scripts/ingest_kb.py",
    "scripts/phase-3-baseline/run_smoke_tests.py",
    "scripts/phase-3-baseline/verify_freeze.py",
    "src/app/__init__.py",
    "src/app/baseline/*.py",
    "src/app/baseline/**/*.py",
    "src/app/baseline_main.py",
    "src/app/core/*.py",
    "src/app/domain/*.py",
    "src/app/infrastructure/**/*.py",
    "src/app/rag/*.py",
    "src/app/tools/*.py",
    "tests/__init__.py",
    "tests/README.md",
    "tests/conftest.py",
    "tests/baseline/**/*.py",
    "tests/shared/**/*.py",
)

COMPARABLE_KEYS = (
    "manifest_schema_version",
    "freeze_id",
    "app_version",
    "source_files",
    "aggregate_sha256",
)


class FreezeScopeError(RuntimeError):
    """Raised when the declared freeze scope cannot be resolved safely."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _frozen_files() -> list[Path]:
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
    return sorted(files, key=lambda path: path.as_posix())


def build_freeze_payload() -> dict[str, Any]:
    """Hash every declared Phase 3 file and derive a canonical aggregate digest."""
    hashes = {
        path.relative_to(PROJECT_ROOT).as_posix(): _sha256(path.read_bytes())
        for path in _frozen_files()
    }
    aggregate = _sha256(json.dumps(hashes, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return {
        "manifest_schema_version": 1,
        "freeze_id": BASELINE_FREEZE_ID,
        "app_version": APP_VERSION,
        "source_files": hashes,
        "aggregate_sha256": aggregate,
    }


def _comparable_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload.get(key) for key in COMPARABLE_KEYS}


def _write_manifest(payload: Mapping[str, Any]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = MANIFEST_PATH.with_suffix(f"{MANIFEST_PATH.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(MANIFEST_PATH)


def describe_freeze_differences(
    expected: Mapping[str, Any], current: Mapping[str, Any]
) -> list[str]:
    """Return stable, reviewable diagnostics for a manifest mismatch."""
    differences: list[str] = []
    for key in ("manifest_schema_version", "freeze_id", "app_version"):
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
        differences.append("aggregate_sha256 does not match the frozen source hashes")
    return differences


def main() -> int:
    """Run manifest write or verification mode from command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Write or verify the cryptographic Phase 3 control freeze manifest."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the named freeze manifest after deliberate Phase 3 changes.",
    )
    arguments = parser.parse_args()
    try:
        current = build_freeze_payload()
    except FreezeScopeError as error:
        print(f"Phase 3 freeze scope is invalid: {error}")
        return 1

    if arguments.write:
        payload = {
            **current,
            "frozen_at": datetime.now(UTC).isoformat(),
        }
        _write_manifest(payload)
        print(f"Wrote {BASELINE_FREEZE_ID}: {current['aggregate_sha256']}")
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

    comparable_expected = _comparable_payload(expected)
    if current != comparable_expected:
        print("Phase 3 freeze verification failed: frozen control files changed.")
        for difference in describe_freeze_differences(comparable_expected, current):
            print(f"- {difference}")
        return 1
    print(f"Verified {BASELINE_FREEZE_ID}: {current['aggregate_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
