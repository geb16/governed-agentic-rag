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
