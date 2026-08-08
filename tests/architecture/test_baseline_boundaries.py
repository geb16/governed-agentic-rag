"""Static dependency tests for the Phase 3 clean-architecture boundary."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[2] / "src" / "app"
PROJECT_ROOT = SOURCE_ROOT.parents[1]


def test_inner_layers_do_not_import_outbound_adapters() -> None:
    """Keep domain and application code independent of concrete adapters."""
    forbidden = ("app.persistence", "app.rag", "app.tools", "app.baseline")
    violations: list[str] = []

    for layer in (SOURCE_ROOT / "application", SOURCE_ROOT / "domain"):
        for source_path in layer.rglob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    imported_names = [node.module]
                else:
                    continue
                for imported_name in imported_names:
                    if imported_name.startswith(forbidden):
                        relative_path = source_path.relative_to(SOURCE_ROOT)
                        violations.append(f"{relative_path}: {imported_name}")

    assert violations == []


def test_removed_compatibility_paths_have_no_callers() -> None:
    """Prevent deleted model compatibility modules from re-entering the import graph."""
    removed_modules = {"app.baseline.model", "app.persistence.models"}
    assert not (SOURCE_ROOT / "baseline" / "model.py").exists()
    assert not (SOURCE_ROOT / "persistence" / "models.py").exists()

    violations: list[str] = []
    for search_root in (SOURCE_ROOT, PROJECT_ROOT / "tests"):
        for source_path in search_root.rglob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module in removed_modules:
                    violations.append(str(source_path.relative_to(PROJECT_ROOT)))
                if isinstance(node, ast.Import):
                    if any(alias.name in removed_modules for alias in node.names):
                        violations.append(str(source_path.relative_to(PROJECT_ROOT)))

    assert violations == []
