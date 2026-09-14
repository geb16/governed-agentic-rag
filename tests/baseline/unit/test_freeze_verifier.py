from __future__ import annotations

from scripts.phase_3_baseline.verify_freeze import (
    FROZEN_PATTERNS,
    build_freeze_payload,
    describe_freeze_differences,
)


def test_freeze_scope_covers_clean_architecture_and_phase3_contracts() -> None:
    payload = build_freeze_payload()
    source_files = payload["source_files"]

    assert isinstance(source_files, dict)
    assert {
        "docker-compose.yml",
        "scripts/ingest_kb.py",
        "scripts/phase-3-baseline/run_smoke_tests.py",
        "scripts/phase-3-baseline/verify_freeze.py",
        "docs/phase-3-baseline/architecture.md",
        "docs/phase-3-baseline/README.md",
        "src/app/baseline/experiments/manifest.py",
        "src/app/baseline/application/service.py",
        "src/app/baseline/composition.py",
        "src/app/infrastructure/llm/openai_responses.py",
        "src/app/infrastructure/persistence/sqlite/repository.py",
        "tests/README.md",
        "tests/baseline/architecture/test_baseline_boundaries.py",
        "tests/baseline/integration/test_agent.py",
        "tests/baseline/integration/test_experiment_manifest.py",
    } <= source_files.keys()
    assert "src/app/core/experiment_manifest.py" not in source_files
    assert "tests/shared/integration/test_experiment_manifest.py" not in source_files
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
