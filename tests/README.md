# Test architecture

Executable tests are grouped by experimental ownership. Baseline and shared tests are then divided
by scope; architecture checks remain top-level because they govern dependencies across ownership
boundaries.

```text
tests/
|-- baseline/
|   |-- unit/          Isolated Phase 3 baseline behaviour
|   `-- integration/   Baseline API and cross-component behaviour
|-- shared/
|   |-- unit/          Configuration and security primitives
|   `-- integration/   Knowledge, tools, retrieval, and persistence
|-- architecture/      Static dependency and module-boundary assertions
|-- support/           Reusable test doubles and composition helpers
`-- conftest.py        Governance-neutral fixtures only
```

Scope names have the following consistent meanings:

- `unit`: one isolated unit with no external service or persistent boundary;
- `component`: one bounded subsystem with controlled local collaborators, when that intermediate
  scope is needed;
- `integration`: API, SQLite, retrieval, workflow, or cross-component behaviour;
- `architecture`: source-structure and dependency-direction constraints.

Test modules must not import `conftest.py`. Shared fixtures are requested by name;
explicit builders and doubles belong in `tests.support`. New tests must be placed in the narrowest
ownership and scope directory that expresses their contract.

Run the complete suite or one explicit boundary:

```console
uv run pytest
uv run pytest tests/baseline
uv run pytest tests/shared
uv run pytest tests/architecture
```
