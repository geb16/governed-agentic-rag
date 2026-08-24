"""Static dependency tests for the Phase 3 clean-architecture boundary."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[3] / "src" / "app"
PROJECT_ROOT = SOURCE_ROOT.parents[1]
REQUIRED_ARCHITECTURE_PATHS = (
    "baseline/api/contracts.py",
    "baseline/api/routes_baseline.py",
    "baseline/application/contracts.py",
    "baseline/application/ports.py",
    "baseline/application/service.py",
    "baseline/agent.py",
    "baseline/experiments/manifest.py",
    "baseline/tool_router.py",
    "core/config.py",
    "domain/actions.py",
    "domain/contracts.py",
    "domain/evidence.py",
    "domain/model.py",
    "domain/repositories.py",
    "domain/support.py",
    "domain/tasks.py",
    "infrastructure/llm/openai_responses.py",
    "infrastructure/persistence/sqlite/repository.py",
    "rag/retriever.py",
    "tools/registry.py",
    "baseline/composition.py",
    "baseline_main.py",
)
DOMAIN_FORBIDDEN_IMPORTS = (
    "app.api",
    "app.application",
    "app.baseline",
    "app.composition",
    "app.core",
    "app.governance",
    "app.infrastructure",
    "app.main",
    "app.persistence",
    "app.rag",
    "app.tools",
)
APPLICATION_FORBIDDEN_IMPORTS = (
    "app.baseline.agent",
    "app.baseline.api",
    "app.baseline.composition",
    "app.baseline.experiments",
    "app.baseline.tool_router",
    "app.governance",
    "app.infrastructure",
    "app.baseline_main",
    "app.rag",
    "app.tools",
)
API_FORBIDDEN_IMPORTS = (
    "app.baseline.agent",
    "app.baseline.composition",
    "app.baseline.experiments",
    "app.baseline.tool_router",
    "app.governance",
    "app.infrastructure",
    "app.baseline_main",
    "app.rag",
    "app.tools",
)


def _imported_names(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_names.append(node.module)
    return imported_names


def _forbidden_import_violations(
    layer: Path,
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []
    source_paths = [layer] if layer.is_file() else layer.rglob("*.py")
    for source_path in source_paths:
        for imported_name in _imported_names(source_path):
            if any(
                imported_name == prefix or imported_name.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            ):
                relative_path = source_path.relative_to(SOURCE_ROOT)
                violations.append(f"{relative_path}: {imported_name}")
    return sorted(violations)


def test_declared_architecture_paths_exist() -> None:
    """Fail when a documented Phase 3 layer or composition entry point is missing."""
    missing = [path for path in REQUIRED_ARCHITECTURE_PATHS if not (SOURCE_ROOT / path).exists()]

    assert missing == []


def test_inner_layers_do_not_import_outbound_adapters() -> None:
    """Keep domain independent and baseline application free of outer adapters."""
    violations = _forbidden_import_violations(
        SOURCE_ROOT / "domain",
        DOMAIN_FORBIDDEN_IMPORTS,
    )
    violations.extend(
        _forbidden_import_violations(
            SOURCE_ROOT / "baseline" / "application",
            APPLICATION_FORBIDDEN_IMPORTS,
        )
    )

    assert sorted(violations) == []


def test_api_depends_on_application_boundary_not_concrete_adapters() -> None:
    """Keep baseline HTTP entry points independent of concrete outbound adapters."""
    violations = _forbidden_import_violations(
        SOURCE_ROOT / "baseline" / "api",
        API_FORBIDDEN_IMPORTS,
    )

    assert violations == []
