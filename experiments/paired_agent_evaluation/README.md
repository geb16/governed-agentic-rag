# Paired Agent Evaluation — Phase 6 Experimental Harness

This isolated project compares the frozen conventional baseline and governance-aware workflow
under identical Phase 5 cases, model, Qdrant collection, synthetic database fixture, simulated
tools, and deterministic failure plan.

The implementation uses the domain name `paired_agent_evaluation`; phase numbers appear only in
documentation and docstrings. It is versioned independently of `src/app` and is **not** frozen —
no identity manifest pins its own code, so defects found here may be fixed directly, without a
phase release. It does, however, verify the Phase 3, 4, and 5 freeze identities it depends on; see
[architecture](../../docs/architecture/phase6_evaluation_architecture.md) for the full design and
[limitations](../../docs/phase-6-experiments/limitations.md) for known compromises.

Mutable run output is written to the gitignored `artifacts/paired_agent_evaluation/`. Only a
completed, adjudicated, sanitized **test**-split run can be sealed under
`data/evaluation/paired_agent_evaluation/v1/`.

## Prerequisites

- Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).
- A running Qdrant instance with the frozen `phase3_enterprise_kb` collection populated (see the
  repository root's own setup instructions).
- A **repository-root** `.env` (this directory has no `.env` of its own) defining at minimum:

  ```
  RAG_RETRIEVAL_BACKEND=qdrant
  RAG_QDRANT_URL=http://localhost:6333
  RAG_OPENAI_API_KEY=...
  RAG_SAFETY_IDENTIFIER_SECRET=...
  ```

  `RAG_EXECUTION_PROFILE=experiment` and `RAG_EXPERIMENT_RUN_ID` are set automatically per run by
  `composition.prepare_run` — do not set them yourself.

This project has its own `pyproject.toml`, `uv.lock`, and `.venv`, independent of the repository
root's. Always pass `--project experiments/paired_agent_evaluation` (or run from inside this
directory) so `uv` resolves the correct environment.

## Readiness gates

From the repository root:

```bash
uv sync --project experiments/paired_agent_evaluation --group dev --frozen
uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_harness.py
uv run --project experiments/paired_agent_evaluation pytest -c experiments/paired_agent_evaluation/pyproject.toml experiments/paired_agent_evaluation/tests
uv run --project experiments/paired_agent_evaluation ruff check experiments/paired_agent_evaluation
uv run --project experiments/paired_agent_evaluation mypy --config-file experiments/paired_agent_evaluation/pyproject.toml
```

