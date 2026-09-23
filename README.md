# Governed Agentic RAG

> Design and evaluation of a governance-aware workflow layer for reliable enterprise agentic RAG

This research project compares a conventional agentic retrieval-augmented generation (RAG)
baseline with a governance-aware workflow under the same knowledge, model configuration,
simulated tools, and synthetic support state. It evaluates reliability, safety, traceability,
groundedness, and recovery without connecting to production enterprise systems.

## Project phases

Each phase has one authoritative guide containing its architecture, operating procedure, tests,
and reproducibility requirements.

| Phase | Purpose | Documentation | Frozen identity |
| --- | --- | --- | --- |
| 3 — Baseline | Conventional agentic RAG control condition | [Phase 3 guide](docs/phase-3-baseline/README.md) | [`phase3-baseline-v5`](docs/phase-3-baseline/freeze-manifest.json) |
| 4 — Governance | Governance-aware workflow condition | [Phase 4 guide](docs/phase-4-governance/README.md) | [`phase4-governance-v6`](docs/phase-4-governance/freeze-manifest.json) |
| 5 — Evaluation | Frozen dataset, schemas, and scoring rubric | [Phase 5 guide](docs/phase-5-evaluation/README.md) | [`phase5-evaluation-v5`](docs/phase-5-evaluation/freeze-manifest.json) |
| 6 — Experiment | Paired, blinded experimental evaluation | [Phase 6 guide](experiments/paired_agent_evaluation/README.md) | [`paired-agent-evaluation-harness-v1`](docs/phase-6-experiments/harness-freeze-manifest.json) |

Supporting design documents are available under [`docs/`](docs/), with external sources collected
in the [project bibliography](docs/references.md). Test ownership and scope are described in
[`tests/README.md`](tests/README.md).

### Documentation conventions

Following [PEP 257](https://peps.python.org/pep-0257/), simple modules in `baseline/` and
`governance/` use concise docstrings to avoid repetition and maintenance overhead, while complex
functions and classes receive more detailed documentation. Development references are cited where
relevant and consolidated in [`docs/references.md`](docs/references.md) for reviewer access.

## Setup

Python 3.11–3.13, [uv](https://docs.astral.sh/uv/), and Docker are required for complete local
execution. Start local configuration from [`.env.example`](.env.example); never commit `.env` or
real credentials.

Install the baseline application environment:

```bash
uv sync --frozen
```

Install the independently locked Phase 6 environment:

```bash
uv sync --project experiments/paired_agent_evaluation --group dev --frozen
```

The default development profile uses lexical retrieval and an isolated SQLite database. Start it
with:

```bash
uv run uvicorn app.baseline_main:app --app-dir src
```

Model-backed execution requires `RAG_OPENAI_API_KEY`. Production and experiment profiles also
require independent `RAG_SAFETY_IDENTIFIER_SECRET` and `RAG_GOVERNANCE_AUDIT_INTEGRITY_KEY`
values. Full experiment reproduction requires the pinned Qdrant service and configuration
described in the [Phase 6 guide](experiments/paired_agent_evaluation/README.md#prerequisites).

## Verify the Phase 6 evidence

From the repository root, verify the inherited Phase 3–5 identities and Phase 6 readiness:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_harness.py
```

Verify the canonical sealed release independently:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py
```

The original v1 release remains preserved as audit history. A deterministic corrective release,
v2, fixes asymmetric normalization of baseline safety blocks without repeating acquisition,
human adjudication, or Ragas grading. Its canonical
[correction record](data/evaluation/paired_agent_evaluation/v2/correction.json) identifies v1 and
the five re-derived files that changed. The earlier
[scoring correction manifest](docs/phase-6-experiments/scoring-correction-manifest.json) separately
records the pre-v1 groundedness-eligibility correction.

Recorded Phase 6 identities:

```text
paired-agent-evaluation-harness-v1
52b04baaeabdddccb93581b2280bb272fbc56eb9562f7d746d13eb09744128ad

paired-agent-evaluation-scoring-correction-v1
cc3f9396d303a2041b56febe330ca74d5c23eedd0f3eb5704fc2953adad781ff

paired-agent-evaluation-v1
150be865736eb274751ddec24f0a084e2d2942c119a25e164600907f492165ea

paired-agent-evaluation-v2
9c8ff4a069535be78c1b76e99e28d9f71255d03ff9bec802c40fdf0b8853115b
```

These verification commands use repository-local evidence. They do not repeat provider calls,
Ragas grading, human adjudication, or experimental acquisition.

## Evidence locations

- [`data/evaluation/paired_agent_evaluation/v2/`](data/evaluation/paired_agent_evaluation/v2/) is
  the canonical, content-addressed Phase 6 corrective release. Its
  [HTML report](data/evaluation/paired_agent_evaluation/v2/report.html) contains the corrected
  primary results.
- [`data/evaluation/paired_agent_evaluation/v1/`](data/evaluation/paired_agent_evaluation/v1/) is
  the superseded original release, retained unchanged for provenance and comparison.
- [`artifacts/paired_agent_evaluation/`](artifacts/paired_agent_evaluation/) is the supporting audit
  trail containing validation runs, the preregistered test run, blinded researcher work,
  schedules, journals, and intermediate execution state.

Both sealed releases remain bound to the exact Phase 3–6 identities recorded in their manifests.
Working artifacts support inspection but do not replace the canonical release.

## Quality gates

Run the repository-level checks with:

```bash
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run pyright
uv run pytest -p no:cacheprovider
uv run pre-commit run --all-files --hook-stage manual
git diff --check
```

The Phase 6 package has its own locked environment and quality gates, documented in its
[readiness section](experiments/paired_agent_evaluation/README.md#readiness-gates).
