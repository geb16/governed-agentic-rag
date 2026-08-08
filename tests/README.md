# Test architecture

The suite is partitioned first by experimental ownership and then by test scope.

```text
tests/
|-- baseline/       Conventional Phase 3 control condition
|-- shared/         Knowledge, tools, configuration, and security substrate
|-- architecture/   Static dependency and module-boundary assertions
|-- support/        Reusable test doubles and composition helpers
`-- conftest.py     Governance-neutral fixtures only
```

Scope names have consistent meanings:

- `unit`: one isolated unit with no external service or persistent boundary;
- `component`: one bounded subsystem with controlled local collaborators;
- `integration`: API, SQLite, retrieval, workflow, or cross-component behaviour;
- `architecture`: source-structure and dependency-direction constraints.

Test modules must not import `conftest.py`. Shared fixtures are requested by name;
explicit builders and doubles belong in `tests.support`.

Run the complete suite or one explicit boundary:

```console
uv run pytest
uv run pytest tests/baseline
uv run pytest tests/shared
uv run pytest tests/architecture
```
