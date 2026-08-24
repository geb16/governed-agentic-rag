"""Static dependency rules for the Phase 4 governance and audit boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src" / "app"
REQUIRED_PATHS = (
    "audit/ports.py",
    "audit/schemas.py",
    "audit/sqlite/repository.py",
    "governance/composition.py",
    "governance/contracts/state.py",
    "governance/llm/ports.py",
    "governance/orchestration/workflow.py",
    "governance/persistence/ports.py",
    "governance/security/settings.py",
    "governance/transport/http/routes.py",
    "governed_main.py",
)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _violations(path: Path, forbidden: tuple[str, ...]) -> list[str]:
    files = [path] if path.is_file() else path.rglob("*.py")
    violations: list[str] = []
    for source in files:
        for imported in _imports(source):
            if any(imported == item or imported.startswith(f"{item}.") for item in forbidden):
                violations.append(f"{source.relative_to(SOURCE_ROOT)}: {imported}")
    return sorted(violations)


def test_phase4_architecture_paths_exist() -> None:
    """Fail explicitly when a declared Phase 4 boundary disappears."""

    assert [path for path in REQUIRED_PATHS if not (SOURCE_ROOT / path).is_file()] == []


def test_audit_is_independent_of_governance_implementation() -> None:
    """Keep the audit vocabulary reusable and free of a governance import cycle."""

    assert _violations(SOURCE_ROOT / "audit", ("app.governance",)) == []


def test_governance_contracts_do_not_import_outer_layers() -> None:
    """Keep workflow contracts independent of orchestration and adapters."""

    assert (
        _violations(
            SOURCE_ROOT / "governance" / "contracts",
            (
                "app.audit",
                "app.governance.composition",
                "app.governance.llm",
                "app.governance.orchestration",
                "app.governance.persistence",
                "app.governance.stages",
                "app.governance.transport",
                "app.governed_main",
            ),
        )
        == []
    )


def test_orchestration_and_stages_do_not_import_concrete_adapters() -> None:
    """Require application flow to use injected ports and stage collaborators."""

    forbidden = (
        "app.audit.sqlite",
        "app.governance.llm.openai_adapter",
        "app.governance.persistence.repository",
        "app.governance.transport",
        "app.governed_main",
    )
    violations = _violations(SOURCE_ROOT / "governance" / "orchestration", forbidden)
    violations.extend(_violations(SOURCE_ROOT / "governance" / "stages", forbidden))

    assert sorted(violations) == []


def test_http_transport_does_not_import_concrete_outbound_adapters() -> None:
    """Keep FastAPI routing independent of SQLite and provider implementations."""

    assert (
        _violations(
            SOURCE_ROOT / "governance" / "transport",
            (
                "app.audit.sqlite",
                "app.governance.llm.openai_adapter",
                "app.governance.persistence",
            ),
        )
        == []
    )
