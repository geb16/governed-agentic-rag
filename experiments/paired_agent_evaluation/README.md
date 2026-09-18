# Paired Agent Evaluation — Phase 6 Experimental Harness

This isolated project compares the frozen conventional baseline and governance-aware workflow
under identical Phase 5 cases, model, Qdrant collection, synthetic database fixture, simulated
tools, and deterministic failure plan.

The implementation uses the domain name `paired_agent_evaluation`; phase numbers appear only in
documentation and docstrings. It is versioned independently of `src/app`. Validation may identify
harness defects, but the corrected harness must be frozen and bound to one completed validation
run and one preregistered test run before the test split can execute. It also verifies the Phase 3,
4, and 5 freeze identities it depends on; see
[architecture](../../docs/architecture/phase6_evaluation_architecture.md) for the full design and
[limitations](../../docs/phase-6-experiments/limitations.md) for known compromises.

Mutable run output is written to the gitignored `artifacts/paired_agent_evaluation/`. Only a
completed, adjudicated, sanitized **test**-split run can be sealed under
`data/evaluation/paired_agent_evaluation/v1/`.

`prepare_run` creates a cryptographically random `blinding-plan.json` before acquisition and pins
its digest in the run manifest. Reviewers receive only `review-packet.jsonl`, whose opaque IDs and
order come from that private plan; never give reviewers the run directory or blinding plan. The
plan is disclosed only in the sealed release after adjudication is final, preserving a verifiable
mapping from reviews to observations without exposing conditions during review.

## Source layout

```text
src/paired_agent_evaluation/
├── domain/               Validated execution, observation, score, and manifest contracts
├── application/          Provider-neutral acquisition, adjudication, scoring, and statistics
├── adapters/             Dataset, system, storage, telemetry, and grader integrations
├── composition/          Paths, run identity, preparation, and acquisition wiring
├── experiment_control/   Readiness, harness freezing, provenance, and one-time authorization
├── reporting/            Primary derivation, persistence, secondary grading, and HTML rendering
└── release/              Artifact policy, independent verification, sanitization, and sealing
```

The package-level `composition`, `experiment_control`, `reporting`, and `release` APIs are stable
entry points for scripts. Internal modules are organized by responsibility and should not be used
as cross-package shortcuts.

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
uv run --project experiments/paired_agent_evaluation ruff format --check experiments/paired_agent_evaluation
uv run --project experiments/paired_agent_evaluation mypy --config-file experiments/paired_agent_evaluation/pyproject.toml
```

`verify_harness.py` must pass all Phase-3, Phase-4, and Phase-5 freeze checks. A failure there
means the defect is upstream, in one of those frozen phases — fix and re-release it there; never
regenerate an inherited manifest from this project to force a pass.

## Controlled experiment sequence

1. Verify the harness and infrastructure, including Qdrant availability and the repository root's
   `.env`.
2. Preview the deterministic schedule if required:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/build_schedule.py --split validation
   ```

3. Acquire the validation split:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/run_validation.py --run-id run_validation_v1
   ```

4. Generate normalized results and the blinded review packet:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_validation_v1
   ```

5. The researcher named in the ethics protocol completes the condition-blinded, field-level
   procedure in
   [scoring and adjudication](../../docs/phase-6-experiments/scoring-and-adjudication.md). Neither an
   LLM nor an automated grader can supply primary review-labels. `review-packet.jsonl` and 
   the two cited guidance documents should only be used while adjudicating. 
   The run directory, condition mapping, or the comparative results should not be inspected.

   Confirm that the submission contains each packet `blinded_id` exactly once, then rerun primary
   scoring without inspecting the condition mapping:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_validation_v1
   ```

   Continue only when `summary.json` records `pending_metric_contributions` as `0` and
   `primary_results_final` as `true`.
6. Run secondary Ragas faithfulness only after the primary human labels are fixed:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_validation_v1 --ragas
   ```

7. Correct harness defects found by validation without changing the frozen metric definitions. If
   the harness changes, reacquire and adjudicate validation with the final candidate code. After
   that validation run is fully scored and adjudicated, freeze the exact harness revision and
   preregister its only permitted test run ID:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_harness.py --write --validation-run-id run_validation_v1 --test-run-id run_test_v1
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_harness.py --frozen
   ```

   Commit and independently review
   `docs/phase-6-experiments/harness-freeze-manifest.json` before test execution. Then acquire the
   untouched test split and generate its initial review packet:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/run_test.py --run-id run_test_v1
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_test_v1
   ```

   Complete the same condition-blinded researcher adjudication used for validation, then rerun
   primary scoring. The secondary Ragas analysis is run only after the `primary_results_final` is true.

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_test_v1
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/score_results.py --run-id run_test_v1 --ragas
   ```

8. Seal exactly one final test run:

   ```bash
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_release.py --seal-run run_test_v1
   uv run --project experiments/paired_agent_evaluation python experiments/paired_agent_evaluation/scripts/verify_release.py
   ```

   Sealing validates the exact scheduled observation identities and independently rederives every
   primary artifact from authoritative inputs. It fails if normalized results, review artifacts,
   scores, estimates, paired differences, or the summary were altered or became stale.

The test split is not a tuning set. Never rerun accepted observations, manually replace model
outputs, or alter labels after viewing comparative results. Each attempt is journaled before system
execution; only an explicitly completed pre-acceptance failure can use the configured bounded retry.
An abandoned started or accepted attempt fails closed and requires investigation instead of an
automatic rerun. Immediately before provider access, `run_test.py` atomically creates
`data/evaluation/paired_agent_evaluation/test-execution-claim.json`; its existence permanently
blocks another local test acquisition. Preserve and commit that claim with the eventual release.

## Troubleshooting

- **`verify_harness.py` fails an inherited freeze gate.** The defect is in Phase 3, 4, or 5, not in
  this harness — fix and re-release the affected phase, then re-run. Do not edit or regenerate that
  phase's freeze manifest from within this project.
- **`run_test.py` rejects the run ID or an existing claim.** Use only the test run ID recorded by
  the reviewed harness freeze. Never delete or replace the execution claim to obtain another run;
  a consumed claim means the test split has already started, even if acquisition was interrupted.
- **`verify_release.py --seal-run` raises on the run's split.** Only a `test`-split run can be
  sealed (`release.sealing.seal_run`); a `validation` run exists to correct the harness before the
  real test-split run, not to be released.
- **`uv` resolves the wrong dependencies or interpreter.** Confirm `--project
  experiments/paired_agent_evaluation` is present (or that you're `cd`'d into this directory) — the
  repository root and this project keep separate lockfiles and virtual environments.

See [architecture](../../docs/phase-6-experiments/architecture.md),
[protocol](../../docs/phase-6-experiments/experimental-protocol.md),
[scoring](../../docs/phase-6-experiments/scoring-and-adjudication.md), and
[limitations](../../docs/phase-6-experiments/limitations.md).
