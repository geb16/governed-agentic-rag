"""Write or verify the cryptographic identity of the Phase 3 baseline."""

from __future__ import annotations

import hashlib

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase-3-freeze-manifest.json"

# Phase 4 governance tests must not alter the Phase 3 identity.
FROZEN_PATTERNS = (
    "pyproject.toml",
    "uv.lock",
    "data/knowledge_base/*",
    "docs/architecture.md",
    "docs/phase-3-baseline.md",
    "scripts/verify_phase3_freeze.py",
    "src/app/__init__.py",
    "src/app/api/*.py",
    "src/app/application/**/*.py",
    "src/app/baseline/*.py",
    "src/app/composition.py",
    "src/app/core/*.py",
    "src/app/domain/*.py",
    "src/app/infrastructure/**/*.py",
    "src/app/main.py",
    "src/app/persistence/*.py",
    "src/app/rag/*.py",
    "src/app/tools/*.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/architecture/test_baseline_boundaries.py",
    "tests/architecture/test_baseline_documentation.py",
    "tests/baseline/**/*.py",
    "tests/shared/**/*.py",
    "tests/support/**/*.py",
    "tests/test_config.py",
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

