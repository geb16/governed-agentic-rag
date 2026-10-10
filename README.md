# Designing and Evaluating a Governed Agentic RAG Workflow for Enterprise Support

> A reproducible, paired comparison of conventional and governance-aware agentic RAG workflows

This research project compares a conventional agentic retrieval-augmented generation (RAG)
baseline with a governance-aware workflow under the same knowledge, model configuration,
simulated tools, and synthetic support state. It evaluates reliability, safety, traceability,
groundedness, and recovery without connecting to production enterprise systems.

## Project phases

Each phase has one authoritative guide containing its architecture, operating procedure, tests,
and reproducibility requirements.

| Phase | Purpose | Documentation | Frozen identity or source |
| --- | --- | --- | --- |
| 3 — Baseline | Conventional agentic RAG control condition | [Phase 3 guide](docs/phase-3-baseline/README.md) | [`phase3-baseline-v5`](docs/phase-3-baseline/freeze-manifest.json) |
| 4 — Governance | Governance-aware workflow condition | [Phase 4 guide](docs/phase-4-governance/README.md) | [`phase4-governance-v7`](docs/phase-4-governance/freeze-manifest.json) |
| 5 — Evaluation | Frozen dataset, schemas, and scoring rubric | [Phase 5 guide](docs/phase-5-evaluation/README.md) | [`phase5-evaluation-v6`](docs/phase-5-evaluation/freeze-manifest.json) |
| 6 — Experiment | Paired, blinded experimental evaluation | [Phase 6 guide](experiments/paired_agent_evaluation/README.md) | [`paired-agent-evaluation-harness-v2`](docs/phase-6-experiments/harness-freeze-manifest-v2.json) |
| 7 — Analysis | Sealed-results analysis and evidence generation | [Phase 7 guide](docs/phase-7-analysis/README.md) | Source: [`paired-agent-evaluation-v4`](data/evaluation/paired_agent_evaluation/v4/manifest.json) |

Supporting design documents are available under [`docs/`](docs/), with external sources collected
in the [project bibliography](docs/references.md). Baseline test ownership is described in the
[`tests/baseline/` guide](tests/baseline/README.md); the Phase 6 guide documents its independently
packaged test suite.

### Architecture diagrams

- [System architecture overview](docs/architectural-diagrams/architectural_diagram.svg) presents
  the baseline and governance-aware workflows with their shared infrastructure and paired
  evaluation.
- [Detailed experimental architecture](docs/architectural-diagrams/architectural_diagram_detailed.svg)
  expands the execution paths, shared substrate, and evaluation boundary.

### Documentation conventions

Following [PEP 257](https://peps.python.org/pep-0257/), simple modules in `baseline/` and
`governance/` use concise docstrings to avoid repetition and maintenance overhead, while complex
functions and classes receive more detailed documentation. Development references are cited where
relevant and consolidated in [`docs/references.md`](docs/references.md) for reviewer access.

## Setup

Python 3.11–3.13, [uv](https://docs.astral.sh/uv/), and Docker are required for complete local
execution. Start local configuration from [`.env.example`](.env.example); never commit `.env` or
real credentials.

Choose `lexical` or `qdrant` explicitly in `.env`, for example:

```dotenv
RAG_RETRIEVAL_BACKEND="lexical"
```

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

> **OpenAI cost warning:** Do not run `run_test.py` or `score_results.py --ragas` merely to verify
> the release. Full test acquisition executes 480 condition-level observations, and Ragas adds
> model-based grading calls. The workflow can exceed 45 minutes and consume substantial API tokens
> and account credit. Use the release-verification command below for inspection without provider
> calls.

## Verify the Phase 6 evidence

From the repository root, verify the inherited Phase 3–5 identities and Phase 6 readiness:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_harness.py \
  --frozen \
  --harness-version 2
```

Verify the canonical sealed release independently:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py --release-version v4
```

Releases v1–v3 remain preserved as superseded audit history. Corrective v2 fixes asymmetric
terminal-error normalization, while corrective v3 fixes baseline route precedence when a
completed human-review request is followed by final-answer citation blocking. Those corrections
did not repeat acquisition, human adjudication, or Ragas grading. The v3
[correction record](data/evaluation/paired_agent_evaluation/v3/correction.json) identifies v2 and
the five re-derived files that changed. Analysis of v3 exposed a governance-escalation defect,
which was corrected before the new harness-v2 experiment. Canonical v4 therefore comes from fresh
validation (`run_validation_v3`), test acquisition (`run_test_v2`), blinded adjudication, primary
scoring, and Ragas grading. The earlier
[scoring correction manifest](docs/phase-6-experiments/scoring-correction-manifest.json) separately
records the pre-v1 groundedness-eligibility correction.

Recorded Phase 6 identities:

```text
paired-agent-evaluation-harness-v1
52b04baaeabdddccb93581b2280bb272fbc56eb9562f7d746d13eb09744128ad

paired-agent-evaluation-harness-v2
587615d92fe1b1596bdee2af48e0d65628e4e77a5345fb3ff1fda71e2bd75efb

paired-agent-evaluation-scoring-correction-v1
cc3f9396d303a2041b56febe330ca74d5c23eedd0f3eb5704fc2953adad781ff

paired-agent-evaluation-v1
150be865736eb274751ddec24f0a084e2d2942c119a25e164600907f492165ea

paired-agent-evaluation-v2
9c8ff4a069535be78c1b76e99e28d9f71255d03ff9bec802c40fdf0b8853115b

paired-agent-evaluation-v3
0f2c281ab19ea6a1c44bf75ad79266c1d51e9a88ee82cd8ea01850561bc7110e

paired-agent-evaluation-v4
017623781efbb1b37b5aec84cbe48f14c3b6bd8d9997a223c23a22f35eccfc10
```

The post-release narrative is bound separately by the
[Phase 6 publication manifest](docs/phase-6-experiments/publication-manifest-v4.1.json), which pins
these documents to the immutable scientific tag, harness v2, and sealed release v4.

These verification commands use repository-local evidence. They do not repeat provider calls,
Ragas grading, human adjudication, or experimental acquisition.

## Evidence locations

- [`data/evaluation/paired_agent_evaluation/v4/`](data/evaluation/paired_agent_evaluation/v4/) is
  the canonical, content-addressed Phase 6 release. Its
  [HTML report](data/evaluation/paired_agent_evaluation/v4/report.html) contains the final primary
  and secondary results.
- [`data/evaluation/paired_agent_evaluation/v1/`](data/evaluation/paired_agent_evaluation/v1/),
  [`v2`](data/evaluation/paired_agent_evaluation/v2/), and
  [`v3`](data/evaluation/paired_agent_evaluation/v3/) are superseded releases retained unchanged
  for provenance and comparison. In particular, v3 preserves the evidence that motivated the
  governance-escalation correction evaluated afresh in v4.
- [`artifacts/paired_agent_evaluation/`](artifacts/paired_agent_evaluation/) is the supporting audit
  trail containing validation runs, the preregistered test run, blinded researcher work,
  schedules, journals, and intermediate execution state.
- [`docs/phase-7-analysis/`](docs/phase-7-analysis/) contains the analysis and reproducible
  figures derived from the sealed Phase 6 release.

All sealed releases remain bound to the exact Phase 3–6 identities recorded in their manifests.
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

## Citation and licence

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). The canonical public release is
[`v1.0.4`](https://github.com/geb16/governed-agentic-rag/tree/v1.0.4).

This project is distributed under the [MIT License](LICENSE).