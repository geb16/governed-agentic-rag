# Phase 7 — Analysis and Dissertation

Phase-7 interprets the immutable Phase-6 test release and prepares dissertation evidence. It does
not reacquire observations, change adjudication, rerun Ragas, or modify any superseded release
under `data/evaluation/paired_agent_evaluation/v1/` or `v2/`.

## Documents

- [Analysis](analysis.md) distinguishes preregistered overall results from exploratory subgroup
  findings and records denominator, failure, cost, and secondary-grading checks.
- [`generated/`](generated/) contains publication-ready SVG figures, CSV tables, and a provenance
  record derived only from the sealed release.

## Reproduce the evidence

First verify the sealed release:

```bash
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py
```

Then regenerate the Phase 7 derivatives:

```bash
uv run python scripts/analysis/generate_evidence.py
```

The generator refuses a source whose release ID, aggregate SHA-256, or member-file digests differ
from `paired-agent-evaluation-v3` / `0f2c281ab19ea6a1c44bf75ad79266c1d51e9a88ee82cd8ea01850561bc7110e`.
The generated [provenance record](generated/provenance.json) binds every table and figure to that
source identity and records the SHA-256 digest of every Python source file in the analysis
pipeline. Corrective v3 preserves v1 and v2 as superseded audit history and changes only the five
derived files declared in its
[`correction.json`](../../data/evaluation/paired_agent_evaluation/v3/correction.json).

## Interpretation rules

- `governed minus baseline` is the reported paired effect.
- Positive effects favour governance only for higher-is-better metrics. False escalation is
  lower-is-better, so a positive difference is adverse.
- Confidence intervals are descriptive, pointwise 95% case-cluster bootstrap intervals. They are
  not hypothesis tests and are not adjusted for multiplicity.
- `NA` means the registered denominator was zero or too few bootstrap replicates were estimable;
  it does not mean zero performance.
- Overall preregistered results lead the findings. Category, route, intent, and risk breakdowns are
  exploratory and are used to explain heterogeneity, not to manufacture a favourable conclusion.
