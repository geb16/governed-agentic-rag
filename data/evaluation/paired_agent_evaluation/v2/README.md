# Paired Agent Evaluation — Corrective Release v2

This release re-derives primary results from the unchanged `run_test_v1` observations and blinded
adjudication. It corrects baseline safety-block normalization so the existing terminal-success
requirement is applied symmetrically to both conditions.

[`correction.json`](correction.json) identifies the superseded v1 aggregate and the derived files
that changed. Acquisition, raw observations, human adjudication, and secondary Ragas grades were
not repeated or modified.

Verify this release from the repository root:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py --release-version v2
```
