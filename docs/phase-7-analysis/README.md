# Phase 7 — Evidence Analysis

Phase 7 turns the immutable Phase 6 release into reviewable tables, figures, and statistical
interpretation. It never reacquires observations, changes adjudication, reruns Ragas, or modifies
sealed evidence.

## Start here

- [Analysis](analysis.md): primary results, denominators, operational trade-offs, exploratory
  findings, and evidence limitations.
- [`generated/`](generated/): publication-ready SVG figures, CSV tables, and cryptographic
  provenance.

## Verify and regenerate

Verify the source release:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py --release-version v4
```

Regenerate its Phase 7 derivatives:

```bash
uv run python scripts/analysis/generate_evidence.py
```

The generator accepts only `paired-agent-evaluation-v4`, aggregate SHA-256
`017623781efbb1b37b5aec84cbe48f14c3b6bd8d9997a223c23a22f35eccfc10`, with every member digest
intact. Its [provenance record](generated/provenance.json) binds each derivative to that release and
to the analysis source code.

Release v4 contains new harness-v2 observations, adjudication, scoring, and Ragas grades from
`run_test_v2`; v1–v3 remain immutable audit history. Because the same test cases informed earlier
development, v4 is a corrective evaluation, not an independent holdout replication.

## Interpretation rules

- Effects are governed minus baseline; negative false-escalation effects favour governance because
  lower is better.
- The pointwise 95% case-cluster bootstrap intervals are descriptive, not multiplicity-adjusted
  hypothesis tests.
- `NA` means non-estimable, not zero performance.
- Preregistered overall results lead; subgroup results are exploratory.
