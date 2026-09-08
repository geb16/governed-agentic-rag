# Phase-6 evaluation architecture

## Purpose and declared scope

Phase-6 is the paired evaluation harness that compares the frozen `phase3-baseline-v3` control and
`phase4-governance-v4` treatment under the same `phase5-evaluation-v3` cases, model, Qdrant
collection, synthetic database fixture, simulated tools, and deterministic failure plan. It answers
whether the governance-aware workflow layer measurably improves reliability, safety, traceability,
and groundedness relative to the conventional baseline — it does not itself implement either
condition. The detailed protocol, scoring, and limitations are maintained in
[Phase 6 experimental protocol](../phase-6-experiments/experimental-protocol.md),
[Phase 6 scoring and adjudication](../phase-6-experiments/scoring-and-adjudication.md), and
[Phase 6 limitations](../phase-6-experiments/limitations.md); this document covers the harness's own
structure, not the experimental design it executes.

## Independent project boundary

Unlike Phase 4 (`app.governance`, a vertical feature package inside the frozen `src/app` tree),
Phase 6 lives entirely outside `src/app` as its own versioned project:
`experiments/paired_agent_evaluation/`, with its own `pyproject.toml`, `uv.lock`, dependency group,
ruff/mypy configuration, and test suite. It depends on the root `governed-agentic-rag` package as an
editable path dependency (`[tool.uv.sources]`) so it can import the frozen `app.baseline`,
`app.governance`, `app.evaluation`, `app.rag`, and `app.core` modules without those modules ever
depending back on it. `tests/architecture/test_boundaries.py::test_evaluation_is_outside_every_frozen_source_scope`
enforces this: the project root must never resolve inside `src/app/baseline`, `src/app/governance`,
or `src/app/evaluation`.

Phase 6's own tests stay under `experiments/paired_agent_evaluation/tests/`, not `tests/`. The root
`tests/evaluation/**` tree is part of the frozen Phase 5 release surface (hashed by
`scripts/verify_phase5_freeze.py`); adding Phase 6 test files there would silently expand what a
Phase 5 refreeze certifies. Splitting the test tree this way keeps the frozen surface and the
actively-developed harness independently verifiable and independently freezable.

The implementation uses the domain name `paired_agent_evaluation` throughout code, directories, and
identifiers; "Phase 6" appears only in documentation, docstrings, and comments, matching how Phase 3
uses `baseline` and Phase 4 uses `governance` rather than phase numbers in code.
