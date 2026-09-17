import ast


def test_evaluation_is_outside_every_frozen_source_scope(paths) -> None:
    assert paths.project == paths.repository / "experiments" / "paired_agent_evaluation"
    assert all(
        not paths.project.is_relative_to(frozen_root)
        for frozen_root in (
            paths.repository / "src" / "app" / "baseline",
            paths.repository / "src" / "app" / "governance",
            paths.repository / "src" / "app" / "evaluation",
        )
    )


def test_domain_layer_does_not_import_adapters_or_application(paths) -> None:
    domain = paths.project / "src" / "paired_agent_evaluation" / "domain"
    for path in domain.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "paired_agent_evaluation.adapters" not in text
        assert "paired_agent_evaluation.application" not in text


def test_application_layer_does_not_import_adapters_or_composition(paths) -> None:
    application = paths.project / "src" / "paired_agent_evaluation" / "application"
    for path in application.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "paired_agent_evaluation.adapters" not in text
        assert "paired_agent_evaluation.composition" not in text


def test_modules_remain_bounded(paths) -> None:
    source = paths.project / "src" / "paired_agent_evaluation"
    oversized = [
        path.relative_to(source)
        for path in source.rglob("*.py")
        if len(path.read_text(encoding="utf-8").splitlines()) > 350
    ]
    assert oversized == []


def test_public_source_api_has_docstrings(paths) -> None:
    source = paths.project / "src" / "paired_agent_evaluation"
    missing = []
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") and ast.get_docstring(node) is None:
                    missing.append(f"{path.relative_to(source)}:{node.lineno}:{node.name}")
    assert missing == []


def test_mutable_run_artifacts_are_gitignored(paths) -> None:
    rules = (paths.repository / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "/artifacts/paired_agent_evaluation/" in rules
