# Prevent Phase-5 offline code from entering either frozen runtime.

import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize("runtime", [Path("src/app/baseline"), Path("src/app/governance")])
def test_frozen_runtime_does_not_import_evaluation(runtime: Path) -> None:
    offenders: list[str] = []
    for path in runtime.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "app.evaluation"
            ):
                offenders.append(str(path))
            if isinstance(node, ast.Import):
                if any(alias.name.startswith("app.evaluation") for alias in node.names):
                    offenders.append(str(path))
    assert not offenders
