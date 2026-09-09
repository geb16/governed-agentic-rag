# Paired Agent Evaluation — Sealed Release v1

This directory holds the sanitized, content-addressed release of the Phase 6 paired evaluation.
It is empty until `experiments/paired_agent_evaluation/scripts/verify_release.py --seal-run
<run-id>` seals exactly one completed, adjudicated **test**-split run (`seal_run` in
`experiments/paired_agent_evaluation/src/paired_agent_evaluation/release.py` refuses any other
split). 