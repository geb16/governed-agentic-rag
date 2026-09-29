# Phase 7 Evidence Analysis

## Evidence boundary

This analysis uses only Phase 6 release `paired-agent-evaluation-v4`, aggregate SHA-256
`017623781efbb1b37b5aec84cbe48f14c3b6bd8d9997a223c23a22f35eccfc10`. Test run `run_test_v2`
contains 80 cases, three repetitions, two conditions, 480 accepted observations, no invalid
observations, and no unresolved primary contributions.

V4 contains new harness-v2 acquisition, blinded adjudication, scoring, and Ragas grades. V1–v3 are
unpooled audit history. Because the same cases informed earlier treatment development, v4 is a
corrective evaluation—not an independent confirmation.

The study estimates performance in a controlled synthetic enterprise-support benchmark. It does
not estimate production prevalence or establish universal superiority.

## Preregistered overall results

| Metric | Baseline | Governed | Governed − baseline (95% CI) | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Appropriate route | 0.508 | 0.725 | +0.217 [0.096, 0.337] | Favourable routing difference in this benchmark. |
| Workflow completion | 0.280 | 0.827 | +0.547 [0.317, 0.756] | Large favourable difference on eligible answer/execute tasks. |
| Action correctness | 0.281 | 0.719 | +0.439 [0.231, 0.646] | Large favourable difference on eligible actionable tasks. |
| Unsafe-action prevention | 1.000 | 1.000 | 0.000 [0.000, 0.000] | Both conditions prevented every registered unsafe action. |
| Approval-control accuracy | 0.000 | 0.606 | +0.606 [0.385, 0.806] | Governance completed 20 of 33 registered approval behaviours. |
| Escalation recall | 0.879 | 0.970 | +0.091 [−0.048, 0.242] | Point estimate favours governance, but the interval crosses zero. |
| Escalation precision | 0.580 | 0.941 | +0.361 [0.142, 0.576] | Governance produced substantially fewer false positive escalations. |
| Escalation F1 | 0.699 | 0.955 | +0.256 [0.101, 0.457] | Combined escalation performance favours governance. |
| False-escalation rate | 0.101 | 0.010 | −0.092 [−0.162, −0.030] | Favours governance because lower is better. |
| Recovery success | 0.125 | 0.792 | +0.667 [0.111, 1.000] | Favourable difference, with a wide interval from the small eligible set. |
| Safe termination | 0.000 | 0.000 | 0.000 [0.000, 0.000] | Both missed the exact registered safe-termination outcome. |
| Groundedness | 0.704 | 1.000 | +0.296 [0.056, 0.588] | Favourable among eligible, non-terminal responses; see denominator warning below. |
| Context precision | 0.250 | 0.250 | 0.000 [0.000, 0.000] | Identical retrieval precision under the shared four-document substrate. |
| Audit completeness | 0.550 | 0.846 | +0.295 [0.275, 0.316] | Consistent, precisely estimated traceability improvement. |

The [machine-readable results](generated/overall-results.csv) contain the exact values. Figure 1
shows all registered paired effects; Figure 2 compares selected condition estimates.

![Overall paired effects](generated/figure-1-overall-effects.svg)

![Selected overall condition estimates](generated/figure-2-condition-estimates.svg)

### Denominators and non-estimability

Metric denominators follow the frozen eligibility rules, not the 240 observations per condition:
workflow completion used 75; action correctness 57; unsafe-action prevention 165; approval and
escalation recall 33; recovery 24; safe termination 15; context precision 156; and audit
completeness 240. Groundedness used 27 baseline and 66 governed responses. These differences reflect
metric eligibility and terminal states, not missing records.

`NA` is distinct from zero: it denotes a zero registered denominator or too few estimable bootstrap
replicates. No overall v4 point estimate is `NA`; sparse exploratory strata may still be
non-estimable.

### Groundedness qualification

Groundedness is conditional on eligible non-terminal responses. Governance produced 150 terminal
outcomes—75 `missing_citation`, 54 `clarification_required`, 15 `governance_denied`, and six
`approval_rejected`—leaving 90 without a terminal error and 66 groundedness-eligible. Its 1.000
estimate means those 66 passed citation-membership and claim-support checks; it does not mean every
request produced a grounded answer. Baseline produced 157 terminal outcomes, including 116
`fabricated_citation` and 24 `missing_citation`, leaving 83 without a terminal error and 27 eligible.

V2 and v3 corrected deterministic normalization of the earlier run. V3 analysis then exposed a
treatment defect. Harness v2 therefore acquired fresh validation and test evidence; v4 does not
reuse earlier observations, adjudication, or Ragas grades.
