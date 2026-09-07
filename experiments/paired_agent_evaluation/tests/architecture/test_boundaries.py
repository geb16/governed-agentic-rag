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

