# Phase 3 baseline tests

Executable contracts for the Phase 3 conventional agentic RAG baseline (`src/app/baseline`,
`src/app/baseline_main.py`, and `scripts/baseline`). Every test is deterministic and offline: model
calls use scripted doubles, retrieval is local, and SQLite state lives in a per-test `tmp_path`.

These files are part of the Phase 3 freeze scope. Any change must be followed by a deliberate
`scripts/baseline/verify_freeze.py --write`.

## Layout

```text
tests/baseline/
|-- architecture/   Static import and dependency-direction constraints
|-- integration/    HTTP, SQLite, retrieval, and cross-component behaviour with real local adapters
|-- unit/           Isolated units with in-file fakes and no persistent boundary
`-- support.py      Baseline-owned test doubles and composition helpers
```

Place a new test in the narrowest scope that expresses its contract. Shared fixtures come from
`tests/conftest.py` and are requested by name; never import `conftest.py`.

## Running

```console
uv run pytest tests/baseline
uv run python scripts/baseline/run_smoke_tests.py
```
The smoke script runs `test_health.py`, `test_api.py`, and one grounded-agent test from this
directory, plus the frozen tool-registry check in `tests/shared`.