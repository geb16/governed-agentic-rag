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

## Dependency and composition model

The project follows the same feature-owned clean architecture as the frozen phases, scaled down to
four layers under `src/paired_agent_evaluation/`:

```text
domain/          Pydantic contracts: execution identities, the schedule, raw and normalized
                 observations, scores, and content-addressed run/release manifests.
application/     Pure orchestration over ports: acquisition, normalization, adjudication,
                 scoring, statistics, scheduling. No adapter or provider imports.
adapters/        Concrete implementations of application ports:
                   dataset/   — Phase5Dataset, reading the frozen Phase 5 release
                   systems/   — BaselineSystemRunner, GovernedSystemRunner (invoke the frozen
                                agent/workflow directly, in isolated per-attempt SQLite state)
                   storage/   — atomic, deterministic JSON/JSONL persistence
                   graders/   — RagasFaithfulnessGrader (secondary sensitivity analysis)
                   telemetry/ — trace-fact projection for audit-completeness scoring
composition.py   The project's own composition root: path discovery, config loading, and
                 prepare_run/acquire wiring. Independent of app.baseline_main/app.governed_main.
release.py       Sanitization and content-addressed sealing of a completed run.
reporting.py     Normalization, scoring, and release-packet generation over a run's raw results.
```

`tests/architecture/test_boundaries.py` enforces the two structural rules this implies:
`domain/` must never import `adapters` or `application`, and `application/` must never import
`adapters` or `composition` — so the ports in `application/ports.py`
(`SystemRunner`, `RawExecutionStore`, `SecondaryGroundednessGrader`) are the only contract adapters
implement, and application code stays testable without constructing any concrete adapter. A third
rule (`test_modules_remain_bounded`) caps every source file at 350 lines, keeping each module legible
without an internal decomposition mandate.

## Component ownership

| Component | Owns | Does not own |
|---|---|---|
| `domain/executions.py` | `Condition`, `ExecutionKey`, the immutable `ScheduledExecution`, `ExperimentConfig` | Persistence, scoring math |
| `domain/observations.py` | `RawExecution`, `NormalizedObservation`, `ToolAttempt`, `BusinessState` | Adapter I/O |
| `domain/manifests.py` | `ExperimentManifest`, `ReleaseManifest` | Sealing or hashing logic |
| `domain/scores.py` | Per-observation metric contribution contracts | Aggregation or bootstrap |
| `application/acquisition.py` | Resumable, bounded pre-acceptance retry over a `SystemRunner` port | Concrete runner construction |
| `application/normalization.py` | Mapping heterogeneous raw responses to one observed-route vocabulary | Statistical estimation |
| `application/adjudication.py` | Blinded review-item construction, resolved-label application | Route inference |
| `application/scoring.py` | The 14 frozen Phase 5 metric contributions per observation | Bootstrap estimation |
| `application/statistics.py` | Bootstrap point estimates, paired differences, category strata | Per-observation scoring |
| `application/scheduling.py` | The deterministic seeded paired schedule | Acquisition execution |
| `adapters/dataset` | Loading and freeze-identity verification of the Phase 5 release | Case scheduling or scoring |
| `adapters/systems` | Constructing and invoking one frozen system per attempt, isolated per-attempt SQLite state and recording retrieval | Response interpretation |
| `adapters/storage` | Atomic JSON and JSONL persistence, canonical hashing | Business logic |
| `adapters/graders` | The pinned Ragas 0.4 secondary faithfulness call | Primary scoring |
| `composition.py` | `EvaluationPaths`, config loading, `prepare_run`/`acquire` wiring | Reporting or sealing |
| `release.py` | Sanitization, content-addressed sealing and verification | Score computation |
| `scripts/*.py` | CLI entry points over `composition`/`reporting`/`release` | Business logic |

## Acquisition, scoring, and sealing sequence

```text
verify_harness.py
  -> re-verify Phase 3, Phase 4, and Phase 5 freeze manifests (hard blocker on any failure)
  -> re-verify the deterministic schedule length for both splits

prepare_run(run_id, split)
  -> load experiment.json, the frozen Phase 5 dataset and rubric, build the seeded schedule
  -> build content-addressed configuration and schedule digests
  -> first call: write run-manifest.json + schedule.json
  -> repeat call: compare every immutable field and the schedule hash; raise on any drift

acquire(run_id, split)
  -> for each scheduled execution not yet accepted:
       run the condition's SystemRunner in an isolated workspace, up to
       max_pre_acceptance_attempts times, until AcceptanceStatus.ACCEPTED
       (an accepted observation is written once and never rerun)
  -> write the updated run manifest (accepted/invalid counts)

reporting: normalize -> score -> adjudicate (blinded) -> [ragas, after adjudication] -> summarize
  -> normalize every raw observation into one route/evidence/tool vocabulary
  -> compute the 14 frozen Phase 5 metric contributions
  -> build and, after human resolution, apply the blinded review packet
  -> bootstrap estimates, paired differences, and the run summary

seal_run(run_root, release_root)
  -> require every RELEASE_FILES entry, status == "scored", primary_results_final
  -> require split == "test"  (a validation run can never be sealed as the release)
  -> sanitize (redact secret-shaped keys) and content-address every file
```

## Failure and consistency model

| Condition | Enforced behavior |
|---|---|
| Missing or failed Phase 3/4/5 freeze verification | `verify_harness.py` exits non-zero; acquisition must not proceed |
| Re-running `prepare_run` with a changed configuration, model, backend, or schedule | Raises `Existing run manifest drift`; the original run is never silently altered |
| A pre-acceptance attempt fails (transient/infrastructure failure before an observation is accepted) | Retried up to `max_pre_acceptance_attempts`, each attempt in its own workspace directory |
| An observation is already accepted | Never rerun; acquisition resumes past it unconditionally |
| A governed workflow's live risk assessment requires a role the dataset's expected decisions omit | That one role is skipped, not the whole replay; every available decision is still applied |
| A run's status is not `"scored"` or primary results are not final | `seal_run` refuses to seal |
| A fully scored run's split is `"validation"` | `seal_run` refuses to seal; only a `"test"`-split run may become the release |
| `verify_release` against a sealed directory | Recomputes and compares every file digest and the aggregate digest; any mismatch fails closed |
| Secondary Ragas grading run before adjudication is locked | Not code-enforced today; the protocol in `experiments/paired_agent_evaluation/README.md` requires human labels be fixed first — see known compromises |

Each `BaselineSystemRunner`/`GovernedSystemRunner` attempt constructs a fresh, isolated SQLite
database under its own attempt workspace before invoking the frozen agent or workflow, so conditions
never share or leak mutable state across observations, repetitions, or each other.

## Blinding and data trust boundaries

| Data or artifact | Trust classification | Enforcement boundary |
|---|---|---|
| Raw and normalized observations | Internal, condition-labeled | Never part of the reviewer-facing packet |
| The review packet (`review-packet.jsonl`) | Reviewer-facing | Carries only a `blinded_id`; no `case_id`, `condition`, or raw observation identity |
| Adjudication resolutions | Reviewer-authored, trusted after dual review | Consumed by scoring only after being written back under the real observation identity |
| Secondary Ragas grades | Diagnostic only | Never merged into primary metric contributions |
| Run and release manifests | Content-addressed, internal | Hash every input file; sensitive-key fields redacted before sealing |
| Raw run artifacts (`artifacts/paired_agent_evaluation/`) | Mutable, local, gitignored | Never committed; only a sealed release under `data/evaluation/paired_agent_evaluation/v1/` is |
| Sealed release directory | Immutable once verified | `seal_run` refuses a non-empty destination; `verify_release` re-derives every hash rather than trusting stored values |
