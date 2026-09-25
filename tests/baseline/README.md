# Test architecture

Executable tests are grouped first by experimental ownership and then by scope. Baseline
architecture checks live with the Phase 3 tests whose source boundaries they protect.

```text
tests/
|-- baseline/
|   |-- architecture/  Static Phase 3 dependency and module-boundary assertions
|   |-- integration/   Baseline API and cross-component behaviour
|   |-- unit/          Isolated Phase 3 baseline behaviour
|   `-- support.py     Baseline-owned test doubles and composition helpers
|-- shared/
|   |-- unit/          Configuration and security primitives
|   `-- integration/   Knowledge, tools, retrieval, and persistence
`-- conftest.py        Governance-neutral fixtures only
```

Scope names have the following consistent meanings:

- `unit`: one isolated unit with no external service or persistent boundary;
- `component`: one bounded subsystem with controlled local collaborators, when that intermediate
  scope is needed;
- `integration`: API, SQLite, retrieval, workflow, or cross-component behaviour;
- `architecture`: source-structure and dependency-direction constraints.

Test modules must not import `conftest.py`. Shared fixtures are requested by name;
explicit baseline builders and doubles belong in `tests.baseline.support`. New tests must be placed
in the narrowest ownership and scope directory that expresses their contract.

Run the complete suite or one explicit boundary:

```console
uv run pytest
uv run pytest tests/baseline
uv run pytest tests/shared
uv run pytest tests/baseline/architecture
```
