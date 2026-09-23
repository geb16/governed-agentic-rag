# Phase 7 — Analysis and Dissertation

Phase 7 interprets the immutable Phase 6 test release and prepares dissertation evidence. It does
not reacquire observations, change adjudication, rerun Ragas, or modify any file under
`data/evaluation/paired_agent_evaluation/v1/`.


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
from `paired-agent-evaluation-v1` / `150be865736eb274751ddec24f0a084e2d2942c119a25e164600907f492165ea`.
The generated [provenance record](generated/provenance.json) binds every table and figure to that
source identity.

## Interpretation rules

- `governed − baseline` is the reported paired effect.
- Positive effects favour governance only for higher-is-better metrics. False escalation is
  lower-is-better, so a positive difference is adverse.
- Confidence intervals are descriptive, pointwise 95% case-cluster bootstrap intervals. They are
  not hypothesis tests and are not adjusted for multiplicity.
- `NA` means the registered denominator was zero or too few bootstrap replicates were estimable;
  it does not mean zero performance.
- Overall preregistered results lead the findings. Category, route, intent, and risk breakdowns are
  exploratory and are used to explain heterogeneity, not to manufacture a favourable conclusion.
