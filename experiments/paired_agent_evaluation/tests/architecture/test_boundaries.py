def test_evaluation_is_outside_every_frozen_source_scope(paths) -> None:
    assert paths.project == paths.repository / "experiments" / "paired_agent_evaluation"
    assert not any(
        str(path).startswith(str(paths.project))
        for path in (
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
