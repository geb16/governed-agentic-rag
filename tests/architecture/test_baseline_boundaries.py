from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "app"
PROJECT_ROOT = SOURCE_ROOT.parents[1]
REQUIRED_ARCHITECTURE_PATHS = (
    "api/routes_baseline.py",
    "application/baseline/ports.py",
    "application/baseline/service.py",
    "baseline/agent.py",
    "baseline/tool_router.py",
    "core/config.py",
    "domain/schemas.py",
    "infrastructure/llm/openai_responses.py",
    "persistence/repository.py",
    "rag/retriever.py",
    "tools/registry.py",
    "composition.py",
    "main.py",
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
    "app.api",
    "app.baseline",
    "app.composition",
    "app.governance",
    "app.infrastructure",
    "app.main",
    "app.persistence",
    "app.rag",
    "app.tools",
)
API_FORBIDDEN_IMPORTS = (
    "app.baseline",
    "app.composition",
    "app.governance",
    "app.infrastructure",
    "app.main",
    "app.persistence",
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
    """Keep domain and application code independent of concrete adapters."""
    forbidden = ("app.persistence", "app.rag", "app.tools", "app.baseline")
    violations: list[str] = []
    for relative_path in ("api/dependencies.py", "api/routes_baseline.py"):
        violations.extend(
            _forbidden_import_violations(
                SOURCE_ROOT / relative_path,
                API_FORBIDDEN_IMPORTS,
            )
        )

    assert violations == []


def test_removed_compatibility_paths_have_no_callers() -> None:
    removed_modules = {"app.baseline.model", "app.persistence.models"}
    assert not (SOURCE_ROOT / "baseline" / "model.py").exists()
    assert not (SOURCE_ROOT / "persistence" / "models.py").exists()

    violations: list[str] = []
    for search_root in (SOURCE_ROOT, PROJECT_ROOT / "tests"):
        for source_path in search_root.rglob("*.py"):
            if removed_modules.intersection(_imported_names(source_path)):
                violations.append(str(source_path.relative_to(PROJECT_ROOT)))

    assert sorted(violations) == []
