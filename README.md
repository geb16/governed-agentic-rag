# Governed Agentic RAG
> Design and Evaluation of Governance-Aware Workflow layer for Reliable Enterprise Agentic RAG Systems

Research AI agent for designing and evaluating a governance-aware workflow layer for reliable
enterprise agentic retrieval-augmented generation (RAG). Phase 3 is the conventional agentic RAG
control condition. Later phases compare it with a governed workflow using the same knowledge,
model configuration, simulated tools, and synthetic support state.

The evaluation focuses on reliability, safety, traceability, and groundedness. All supplied action
tools are simulated; the project does not connect to production customer, payment, IAM, ticketing,
or messaging systems.

## Architecture and baseline contract

- [Phase 3 architecture](docs/phase-3-baseline/architecture.md)
- [Phase 3 behavioral, security, and reproducibility contract](docs/phase-3-baseline/README.md)
- [Phase 3 cryptographic freeze identity](docs/phase-3-baseline/freeze-manifest.json)
- [Test ownership and scope](tests/README.md)

The baseline is organized as a feature-owned clean architecture:

```text
src/app/
|-- baseline/          Phase 3 API, application, experiments, façade, and composition
|-- core/              Shared configuration, logging, security, and versions
|-- domain/            Shared task, action, evidence, model, repository, and support contracts
|-- infrastructure/    Shared OpenAI and SQLite adapters
|-- rag/               Shared lexical and Qdrant retrieval
|-- tools/             Shared allowlisted simulated capabilities
`-- baseline_main.py   Phase 3 FastAPI entry point
```

## Local setup

Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/) are required.

```console
uv sync --frozen
uv run uvicorn app.baseline_main:app --app-dir src
```

The default development profile uses lexical retrieval and an isolated local SQLite database.
Open `http://127.0.0.1:8000/api/v1/health/live` to verify liveness. Model-backed invocation requires
`RAG_OPENAI_API_KEY`; production and experiment profiles additionally require
`RAG_SAFETY_IDENTIFIER_SECRET`.

## Qdrant experiment setup

The experiment profile requires the pinned local Qdrant service and a named immutable run.

```console
docker compose up -d qdrant
uv run python scripts/ingest_kb.py
```

Configure:

```text
RAG_EXECUTION_PROFILE=experiment
RAG_RETRIEVAL_BACKEND=qdrant
RAG_QDRANT_URL=http://127.0.0.1:6333
RAG_OPENAI_API_KEY=<provider credential>
RAG_SAFETY_IDENTIFIER_SECRET=<independent pseudonymization secret>
RAG_EXPERIMENT_RUN_ID=run_<unique identifier>
```

Application startup automatically records the experiment manifest under
`artifacts/runs/<run-id>/manifest.json`. Reusing a run identifier with different configuration
fails closed.

## Verification

Run the focused deterministic smoke suite:

```console
uv run python scripts/phase-3-baseline/run_smoke_tests.py
```

Run the complete local gate:

```console
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run pyright
uv run pytest -p no:cacheprovider
uv run pre-commit run --all-files --hook-stage manual
git diff --check
```

The pre-commit hooks are intentionally manual and execute the same locked local tools directly;

## Freeze procedure

Only write a new manifest after all Phase 3 changes are reviewed and committed to the intended
release branch:

```console
uv run python scripts/phase-3-baseline/verify_freeze.py --write
uv run python scripts/phase-3-baseline/verify_freeze.py
git diff -- docs/phase-3-baseline/freeze-manifest.json
```
