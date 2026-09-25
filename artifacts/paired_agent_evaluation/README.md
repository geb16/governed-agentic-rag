# Paired Agent Evaluation Artifacts

This directory preserves the Phase 6 execution audit trail. The canonical sealed release is
[`data/evaluation/paired_agent_evaluation/v3/`](../../data/evaluation/paired_agent_evaluation/v3/).
The original [`v1`](../../data/evaluation/paired_agent_evaluation/v1/) and corrective
[`v2`](../../data/evaluation/paired_agent_evaluation/v2/) releases are preserved unchanged as
superseded audit history; working artifacts here support inspection but do not replace v3.

## Run status

| Run | Status | Purpose |
| --- | --- | --- |
| `run_validation_v1` | Superseded | Historical validation run retained for traceability; it was not used to freeze the final harness. |
| `run_validation_v2` | Final validation | Validation evidence bound by the [Phase 6 harness freeze](../../docs/phase-6-experiments/harness-freeze-manifest.json). |
| `run_test_v1` | Preregistered test | The single preregistered test run and source of the sealed Phase 6 release. |

## Directory conventions

- `researcher-work/` contains reviewer-facing input batches and the researcher's completed batch
  outputs. The authoritative submissions are retained under each run's `adjudication/` directory.
- A run's `work/` directory contains per-observation attempt journals and isolated synthetic SQLite
  state used during acquisition. These are execution internals, not scored results.
- `researcher-work/run_validation_v1/` is intentionally absent. Its superseded researcher workspace
  was deleted to prevent stale material from being mistakenly used for current adjudication evidence. The
  historical `run_validation_v1/` artifacts remain available for audit traceability.

Do not infer final findings from the superseded validation run or intermediate workspaces. Use the
[canonical sealed report](../../data/evaluation/paired_agent_evaluation/v3/report.html) for reported
results.
