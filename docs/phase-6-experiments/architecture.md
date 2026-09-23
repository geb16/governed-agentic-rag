# Phase-6 evaluation architecture

## Purpose and declared scope

Phase-6 is the paired evaluation harness that compares the frozen `phase3-baseline-v5` control and
`phase4-governance-v6` treatment under the same `phase5-evaluation-v5` cases and rubric, model, Qdrant
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
`scripts/evaluation/verify_freeze.py`); adding Phase 6 test files there would silently expand what a
Phase 5 refreeze certifies. Splitting the test tree this way keeps the frozen surface and the
actively-developed harness independently verifiable and independently freezable.

The implementation uses the domain name `paired_agent_evaluation` throughout code, directories, and
identifiers; "Phase 6" appears only in documentation, docstrings, and comments, matching how Phase 3
uses `baseline` and Phase 4 uses `governance` rather than phase numbers in code.

## Dependency and composition model

The project follows the same feature-owned clean architecture as the frozen phases. A three-layer
core sits behind dedicated composition, experiment-control, reporting, and release boundaries under
`src/paired_agent_evaluation/`:

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
composition/     Composition root: controlled paths, run identity, preparation, and acquisition
                 wiring. Independent of app.baseline_main/app.governed_main.
experiment_control/
                 Harness readiness, provenance identity, freeze verification, and atomic
                 authorization for the single preregistered test execution.
reporting/       Primary artifact derivation, persistence and status transitions, optional
                 secondary grading, and deterministic HTML rendering.
release/         Release artifact policy, sanitization, independent verification, and
                 content-addressed sealing of a completed test run.
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
| `domain/executions.py` | Execution, schedule, configuration, and attempt-lifecycle contracts | Persistence, scoring math |
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
| `adapters/storage` | Atomic JSON/JSONL persistence, canonical hashing, and the monotonic attempt journal | Retry policy or system execution |
| `adapters/reproducibility.py` | Non-secret settings, tool-schema, and exact Qdrant point fingerprints | Acquisition or scoring policy |
| `adapters/graders` | The pinned Ragas 0.4 secondary faithfulness call | Primary scoring |
| `composition/paths.py` | `EvaluationPaths` discovery and run-ID path policy | Run construction or acquisition |
| `composition/identity.py` | Configuration, package, schedule, and manifest identities; resume-drift checks | Adapter execution |
| `composition/builder.py` | `prepare_run` and reproducible run initialization | Observation acquisition |
| `composition/acquisition.py` | Concrete runner/storage wiring and `acquire` entry points | Scoring or release policy |
| `experiment_control/readiness.py` | Inherited freeze verification and schedule-cardinality gates | Harness persistence |
| `experiment_control/identity.py` | Controlled source hashes and inherited/validation evidence identities | Test authorization |
| `experiment_control/freeze.py` | Harness freeze creation and verification | Provider execution |
| `experiment_control/authorization.py` | Atomic, one-time preregistered test claim | Harness identity derivation |
| `reporting/derivation.py` | Normalization, blinded adjudication application, primary scoring, estimates, and summary derivation | Persistence or secondary grading |
| `reporting/scoring.py` | Primary artifact persistence, HTML generation, and manifest status transitions | Metric formulas |
| `reporting/secondary_grading.py` | Optional Ragas faithfulness diagnostics | Primary metrics or finality |
| `reporting/visual_report.py` | Deterministic, escaped standalone HTML rendering | Statistical derivation |
| `release/artifacts.py` | Closed release policy, redaction, deterministic serialization, and file hashing | Eligibility or verification |
| `release/verification.py` | Independent primary rederivation and sealed-release integrity checks | Artifact mutation |
| `release/sealing.py` | Test-run eligibility and content-addressed sealing orchestration | Primary scoring |
| `scripts/*.py` | CLI entry points over `composition`, `experiment_control`, `reporting`, and `release` | Business logic |

## Acquisition, scoring, and sealing sequence

```text
verify_harness.py
  -> re-verify Phase 3, Phase 4, and Phase 5 freeze manifests (hard blocker on any failure)
  -> re-verify the deterministic schedule length for both splits
  -> after completed validation: hash the harness and validation evidence; preregister one test ID

run_test.py
  -> re-verify inherited freezes, the harness hash, and pinned completed-validation evidence
  -> require the exact preregistered test run ID
  -> atomically create the durable one-time execution claim before any provider call
  -> refuse every later attempt, including attempts under a different run ID

composition.builder.prepare_run(run_id, split)
  -> load experiment.json, the frozen Phase 5 dataset and rubric, build the seeded schedule
  -> generate one cryptographically random blinding map and reviewer order before acquisition
  -> build content-addressed configuration and schedule digests
  -> first call: write run-manifest.json + schedule.json + private blinding-plan.json
  -> repeat call: compare every immutable field, schedule hash, and blinding-plan hash; raise on drift

composition.acquisition.acquire(run_id, split)
  -> for each scheduled execution without a persisted observation:
       atomically journal STARTED before invoking the condition's SystemRunner
       mark ACCEPTED after the first successful provider response or deterministic local outcome
       retry only a journaled PRE_ACCEPTANCE_FAILED result, up to the configured bound
       persist the raw observation atomically, then close the journal
  -> write the updated run manifest (accepted/invalid counts)

reporting.derivation: normalize -> review packet -> adjudicate (blinded) -> score -> summarize
  -> normalize every raw observation into one route/evidence/tool vocabulary
  -> build the randomly ordered, condition-blinded review packet
  -> validate one condition-blinded researcher decision for each applicable review field
  -> apply resolved labels and compute the 14 frozen Phase 5 metric contributions
  -> bootstrap condition estimates, category-macro estimates, paired differences, and the summary

reporting.secondary_grading.grade_ragas(run_id)
  -> optionally run Ragas only after primary adjudication is final

release.sealing.seal_run(run_root, release_root)
  -> require every RELEASE_FILES entry, status == "scored", primary_results_final
  -> require split == "test"  (a validation run can never be sealed as the release)
  -> validate the exact scheduled observation identity set
  -> independently rederive normalized observations, review artifacts, scores, estimates,
     paired differences, and summary from raw observations and authoritative inputs
  -> reject sealing if any stored primary artifact differs from its rederived value
  -> sanitize (redact secret-shaped keys) and content-address every file

release.sealing.seal_corrective_release(run_root, prior_release_root, release_root, ...)
  -> independently verify the superseded release and source-run manifest identity
  -> rederive primary artifacts from the original immutable test evidence
  -> require raw observations, review packet, and resolved adjudications to match exactly
  -> copy unchanged control and secondary artifacts from the superseded release
  -> record changed derived files in correction.json and verify the new closed release
```

## Failure and consistency model

| Condition | Enforced behavior |
|---|---|
| Missing or failed Phase 3/4/5 freeze verification | `verify_harness.py` exits non-zero; acquisition must not proceed |
| Missing/drifted Phase 6 harness freeze or incomplete/drifted validation evidence | Test acquisition fails before provider access |
| Test run ID differs from the preregistration | Test acquisition fails before creating a run |
| Any prior execution claim, test run manifest, or sealed test release exists | Every later test acquisition is rejected; a new run ID cannot bypass the gate |
| Re-running `prepare_run` with a changed configuration, model, backend, or schedule | Raises `Existing run manifest drift`; the original run is never silently altered |
| A proven pre-acceptance attempt fails | Journaled as `PRE_ACCEPTANCE_FAILED` and retried up to `max_pre_acceptance_attempts`, with every attempt in an isolated workspace |
| A prior attempt remains `STARTED` or `ACCEPTED` without a raw observation | Acquisition fails closed because provider acceptance cannot be safely excluded; no automatic rerun occurs |
| A raw observation is already persisted | Acquisition resumes past it without invoking either system |
| Raw observations are duplicated, missing, or substituted while preserving the expected count | Scoring rejects the run because observation identities must exactly match the frozen schedule |
| A governed workflow's live risk assessment requires a role the dataset's expected decisions omit | That one role is skipped, not the whole replay; every available decision is still applied |
| A run's status is not `"scored"` or primary results are not final | `seal_run` refuses to seal |
| A fully scored run's split is `"validation"` | `seal_run` refuses to seal; only a `"test"`-split run may become the release |
| A stored normalized result, review artifact, score, estimate, paired difference, or summary drifts from deterministic rederivation | `seal_run` refuses to seal, regardless of manifest status |
| `verify_release` against a sealed directory | Recomputes and compares every file digest and the aggregate digest; any mismatch fails closed |
| A corrective release changes authoritative inputs or targets its superseded directory | `seal_corrective_release` fails before publishing a new manifest |
| Secondary Ragas grading run before adjudication is locked | Not code-enforced today; the protocol in `experiments/paired_agent_evaluation/README.md` requires human labels be fixed first — see known compromises |

Each `BaselineSystemRunner`/`GovernedSystemRunner` attempt constructs a fresh, isolated SQLite
database under its own attempt workspace before invoking the frozen agent or workflow, so conditions
never share or leak mutable state across observations, repetitions, or each other.
The runner's model decorator records acceptance only after a provider call returns successfully.
Authentication, connection, and provider-availability failures before that point remain invalid
attempts; failures after recorded acceptance remain system outcomes. The attempt journal is the
durable authority used to prevent an accepted invocation from being silently repeated after a crash.
For governed observations, audit facts are trusted only when the source chain is valid and its
workflow, trace, and request identities correlate with the response and request. Events from an
invalid or mismatched envelope contribute no audit-completeness facts.

## Blinding and data trust boundaries

| Data or artifact | Trust classification | Enforcement boundary |
|---|---|---|
| Raw and normalized observations | Internal, condition-labeled | Never part of the reviewer-facing packet |
| The private blinding plan (`blinding-plan.json`) | Confidential until adjudication is final | Maps observations to cryptographically random opaque IDs and records a random reviewer order; its digest is pinned by the run manifest |
| The review packet (`review-packet.jsonl`) | Reviewer-facing | Carries only opaque IDs in the private plan's random order; no `case_id`, `condition`, raw observation identity, or public derivation input |
| Researcher adjudications | Researcher-authored, condition-blinded | Consumed by scoring through opaque identities; the private plan supplies the observation mapping |
| Secondary Ragas grades | Diagnostic only | Never merged into primary metric contributions |
| Stored primary result artifacts and `report.html` | Derived, not authoritative | `seal_run` rederives and compares them from raw observations, the schedule, dataset, rubric, blinding plan, and adjudication inputs |
| Harness freeze and test-execution claim | Preregistered control evidence | Bind reviewed source bytes and completed validation to one test ID; claim is created exclusively before provider access and copied into the sealed run |
| Run and release manifests | Content-addressed, internal | Hash every input file plus runtime, tool-schema, and Qdrant-content identities; sensitive-key fields are redacted before sealing |
| Raw run artifacts (`artifacts/paired_agent_evaluation/`) | Mutable, local, gitignored | Never canonical; only a verified release under `data/evaluation/paired_agent_evaluation/` is reported |
| Sealed release directory | Immutable once verified | v1 remains preserved as superseded history; v2 is canonical; sealing refuses a non-empty destination and verification recomputes every hash |

## Known architectural compromises

1. `adapters/systems/baseline.py` and `governed.py` are structurally symmetric (construct isolated
   state, invoke the frozen system, project a `RawExecution`) but not shared code, because the two
   frozen systems have different construction signatures and response shapes. A small amount of
   logic — role-alias canonicalization (`ROLE_ALIASES`) in particular — is duplicated between
   `adapters/systems/governed.py` and `application/normalization.py` rather than factored into one
   shared module; the two must be kept in sync by hand.
2. Declarative method labels in `config/reporting.json` and policy text in `config/graders.json`
   are hashed for provenance but do not dynamically select implementations. The corresponding
   executable policies live in `application/statistics.py`, `application/adjudication.py`, and
   `application/scoring.py`; changes therefore require code, configuration, and tests to remain in
   agreement.
3. The Ragas-after-adjudication ordering ("run secondary faithfulness only after primary human
   labels are fixed") is a documented protocol step, not a code-enforced precondition; nothing stops
   `score_results.py --ragas` from running before adjudication is complete.
4. Route and claim-support judgements have one researcher-adjudicator. Condition blinding limits
   bias, but independent replication and inter-rater reliability are unavailable.
5. This harness inherits every architectural compromise of the systems it evaluates (see
   [Phase 4 governance architecture — known architectural compromises](../phase-4-governance/architecture.md#known-architectural-compromises)):
   single-process SQLite durability, synchronous model/tool calls, and an unanchored (though
   tamper-evident) audit hash chain all bound what "governed" and "baseline" can mean in this pilot's
   results.
6. The one-time execution claim is durable repository evidence rather than an external append-only
   registry. Deleting both the claim and all test/release artifacts could bypass the local guard;
   repository permissions and review must therefore prevent removal. The harness still fails closed
   for normal operation, interruption, repeated commands, and alternative run IDs.

## Readiness gates

`experiments/paired_agent_evaluation/scripts/verify_harness.py` is the harness's own composite gate:
it re-verifies all three inherited freeze manifests and the deterministic schedule length for both
splits. Its `--write` mode accepts only completed validation evidence and preregisters one test run;
its `--frozen` mode recomputes every harness, inherited-release, and validation hash. It is necessary
but not sufficient — the full local
gate (`pytest`, `ruff check`, `ruff format --check`, and `mypy`) documented in
`experiments/paired_agent_evaluation/README.md`
must also pass before acquisition begins, since `verify_harness.py` does not itself run the test
suite or static analysis.

## Architecture verification expectations

`experiments/paired_agent_evaluation/tests/architecture/test_boundaries.py` must fail when:

- the project root resolves inside `src/app/baseline`, `src/app/governance`, or `src/app/evaluation`;
- `domain/` imports `adapters` or `application`;
- `application/` imports `adapters` or `composition`;
- any source file under `src/paired_agent_evaluation/` exceeds 350 lines.

These static checks protect dependency direction and module size. They do not replace the frozen
freeze-manifest checks, the local test/lint/type gate, or human review of the experimental protocol
itself.
