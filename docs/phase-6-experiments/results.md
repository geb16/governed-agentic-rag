# Phase 6 Results

The canonical Phase 6 results are sealed under
[`data/evaluation/paired_agent_evaluation/v4/`](../../data/evaluation/paired_agent_evaluation/v4/).
The [HTML report](../../data/evaluation/paired_agent_evaluation/v4/report.html) presents every
registered estimate, paired difference, confidence interval, stratum, and secondary Ragas grade.
The release identity is `paired-agent-evaluation-v4`, with aggregate SHA-256
`017623781efbb1b37b5aec84cbe48f14c3b6bd8d9997a223c23a22f35eccfc10`.

Release v4 contains 480 accepted observations from 80 test cases, three repetitions, and two
conditions; no observation was invalid. The condition-blinded researcher completed all 216 review
items, no primary metric contribution remained pending, and all 440 eligible secondary
`ragas.Faithfulness` grades completed.

## Overall registered results

All effects are governed minus baseline. Confidence intervals are two-sided 95% case-clustered
bootstrap intervals and are descriptive rather than multiplicity-adjusted hypothesis tests.

| Metric | Baseline | Governed | Effect [95% CI] |
| --- | ---: | ---: | ---: |
| Appropriate route | 0.508 | 0.725 | +0.217 [0.096, 0.337] |
| Workflow completion | 0.280 | 0.827 | +0.547 [0.317, 0.756] |
| Action correctness | 0.281 | 0.719 | +0.439 [0.231, 0.646] |
| Unsafe-action prevention | 1.000 | 1.000 | 0.000 [0.000, 0.000] |
| Approval-control accuracy | 0.000 | 0.606 | +0.606 [0.385, 0.806] |
| Escalation recall | 0.879 | 0.970 | +0.091 [-0.048, 0.242] |
| Escalation precision | 0.580 | 0.941 | +0.361 [0.142, 0.576] |
| Escalation F1 | 0.699 | 0.955 | +0.256 [0.101, 0.457] |
| False-escalation rate | 0.101 | 0.010 | -0.092 [-0.162, -0.030] |
| Recovery success | 0.125 | 0.792 | +0.667 [0.111, 1.000] |
| Safe termination | 0.000 | 0.000 | 0.000 [0.000, 0.000] |
| Groundedness | 0.704 | 1.000 | +0.296 [0.056, 0.588] |
| Context precision | 0.250 | 0.250 | 0.000 [0.000, 0.000] |
| Audit-trace completeness | 0.550 | 0.846 | +0.295 [0.275, 0.316] |

Lower is better only for false-escalation rate; its negative effect therefore favours governance.
The escalation-recall interval crosses zero, so its point estimate does not establish a conclusive
difference in this experiment. The sealed report remains authoritative for eligibility,
denominators, category and route strata, latency, token use, and exact unrounded values.

## Release lineage

Releases v1–v3 remain immutable, superseded audit history. Version 2 corrected asymmetric
terminal-error normalization, and v3 corrected baseline route precedence after a completed
human-review request. Their correction records identify every re-derived file and confirm that the
original raw observations, adjudication, schedule, and Ragas grades were unchanged.

Analysis of v3 exposed a genuine governance workflow defect: approval-eligible requests were being
treated as missing-information clarifications instead of entering the approval-routing path. That
system behavior was corrected in `phase4-governance-v7`, then propagated through
`phase5-evaluation-v6`. Because this changed the evaluated treatment, v4 did not reuse the old
test evidence: harness v2 was validated with `run_validation_v3`, preregistered
`run_test_v2`, and repeated acquisition, blinded adjudication, primary scoring, and Ragas grading.

## Reproducibility

The harness command below must be run from a checkout of the immutable scientific tag
`phase6-experimental-evaluation-v4`, whose source bytes match the preregistered freeze. The release
command may be run from either the scientific or publication tag because sealed v4 is unchanged.

```bash
# From phase6-experimental-evaluation-v4:
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_harness.py \
  --frozen \
  --harness-version 2

# From either Phase 6 tag:
uv run --project experiments/paired_agent_evaluation \
  python experiments/paired_agent_evaluation/scripts/verify_release.py \
  --release-version v4
```

The scientific release is preserved by Git tag `phase6-experimental-evaluation-v4`. Subsequent
narrative corrections are publication-layer changes and do not alter sealed v4 or the experimental
artifacts.
