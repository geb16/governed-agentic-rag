"""Write or verify the cryptographic identity of the Phase 3 baseline."""

from __future__ import annotations

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
