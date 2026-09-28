# Paired Agent Evaluation Artifacts

This directory preserves the Phase 6 execution audit trail. The canonical sealed release is
[`data/evaluation/paired_agent_evaluation/v4/`](../../data/evaluation/paired_agent_evaluation/v4/).
Releases [`v1`](../../data/evaluation/paired_agent_evaluation/v1/),
[`v2`](../../data/evaluation/paired_agent_evaluation/v2/), and
[`v3`](../../data/evaluation/paired_agent_evaluation/v3/) are preserved unchanged as superseded
audit history. Version 3 remains important because its analysis exposed the governance-escalation
defect corrected before the fresh v4 experiment. Working artifacts here support inspection but do
not replace the sealed release.

## Run status

| Run | Status | Purpose |
| --- | --- | --- |
| `run_validation_v1` | Superseded | Historical validation run retained for traceability; it was not used to freeze the final harness. |
| `run_validation_v2` | Superseded validation | Validation evidence for harness v1 and the historical v1–v3 release lineage. |
| `run_test_v1` | Historical preregistered test | Test evidence underlying the preserved v1–v3 releases. |
| `run_validation_v3` | Final validation | Validation evidence bound by [harness v2](../../docs/phase-6-experiments/harness-freeze-manifest-v2.json). |
| `run_test_v2` | Final preregistered test | The single harness-v2 test run and source of canonical release v4. |

## Directory conventions

- `researcher-work/` contains reviewer-facing input batches and the researcher's completed batch
  outputs. The authoritative submissions are retained under each run's `adjudication/` directory.
- A run's `work/` directory contains per-observation attempt journals and isolated synthetic SQLite
  state used during acquisition. These are execution internals, not scored results.
- `researcher-work/run_validation_v1/` is intentionally absent. Its superseded researcher workspace
  was deleted to prevent stale material from being mistakenly used for current adjudication evidence. The
  historical `run_validation_v1/` artifacts remain available for audit traceability.

Do not infer final findings from the superseded validation run or intermediate workspaces. Use the
[canonical sealed report](../../data/evaluation/paired_agent_evaluation/v4/report.html) for reported
results.
