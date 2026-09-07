# Paired Agent Evaluation(Experiment phase)

This isolated project is the Phase 6 experimental harness. It compares the frozen conventional
baseline and governance-aware workflow under the same Phase 5 cases, model, Qdrant collection,
synthetic database fixture, simulated tools, and deterministic failure plan.

The implementation uses the domain name `paired_agent_evaluation`; phase numbers appear only in
documentation and docstrings. Mutable work is written to `artifacts/paired_agent_evaluation/`.
Only a completed, adjudicated, sanitized run can be sealed under
`data/evaluation/paired_agent_evaluation/v1/`.

## Readiness gates

From the repository root:

```bash
uv sync --project experiments/paired_agent_evaluation --group dev --frozen
uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_harness.py
uv run --project experiments/paired_agent_evaluation pytest -c experiments/paired_agent_evaluation/pyproject.toml experiments/paired_agent_evaluation/tests
uv run --project experiments/paired_agent_evaluation ruff check experiments/paired_agent_evaluation
uv run --project experiments/paired_agent_evaluation mypy --config-file experiments/paired_agent_evaluation/pyproject.toml
```

`verify_harness.py` must pass all Phase-3, Phase-4, and Phase-5 freeze checks. A failure is a hard
experimental blocker; do not regenerate an inherited manifest from this project.
