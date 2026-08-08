from __future__ import annotations

from scripts.verify_phase3_freeze import (
    FROZEN_PATTERNS,
    build_freeze_payload,
    describe_freeze_differences,
)


def test_freeze_scope_covers_clean_architecture_and_phase3_contracts() -> None:
    payload = build_freeze_payload()
    source_files = payload["source_files"]

    assert isinstance(source_files, dict)
    assert {
        "scripts/verify_phase3_freeze.py",
        "docs/architecture/baseline_architecture.md",
        "docs/phase-3-baseline.md",
        "src/app/application/baseline/service.py",
        "src/app/composition.py",
        "src/app/infrastructure/llm/openai_responses.py",
        "tests/README.md",
        "tests/architecture/test_baseline_boundaries.py",
        "tests/baseline/integration/test_agent.py",
    } <= source_files.keys()
    assert "src/app/baseline/model.py" not in source_files
    assert "src/app/persistence/models.py" not in source_files
    assert "tests/test_config.py" not in source_files
    assert all("__pycache__" not in path for path in source_files)
    assert "tests/governance/**/*.py" not in FROZEN_PATTERNS
    assert "tests/test_config.py" not in FROZEN_PATTERNS


def test_freeze_difference_diagnostics_identify_file_changes() -> None:
    expected = {
        "manifest_schema_version": 1,
        "freeze_id": "phase3-baseline-v1",
        "app_version": "0.1.0",
        "source_files": {
            "removed.py": "old",
            "modified.py": "old",
        },
        "aggregate_sha256": "old-aggregate",
    }
    current = {
        **expected,
        "source_files": {
            "added.py": "new",
            "modified.py": "new",
        },
        "aggregate_sha256": "new-aggregate",
    }

    assert describe_freeze_differences(expected, current) == [
        "added: added.py",
        "removed: removed.py",
        "modified: modified.py",
    ]
