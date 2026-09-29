# Results Analysis (Phase-7)

## Evidence boundary

This analysis uses only the canonical Phase 6 release `paired-agent-evaluation-v4`, aggregate
SHA-256 `017623781efbb1b37b5aec84cbe48f14c3b6bd8d9997a223c23a22f35eccfc10`. The source test run is
`run_test_v2`: 80 test cases, three repetitions, two conditions, 480 accepted observations and no
invalid observations. All primary contributions were resolved before secondary Ragas grading:
`pending_metric_contributions` is zero and `primary_results_final` is true.

Release v4 is a fresh harness-v2 experiment following the Phase 4 governance correction. It uses
new validation, test acquisition, blinded adjudication, primary scoring, and Ragas grading.
Releases v1–v3 remain unchanged as superseded audit history and are not pooled with v4. The v4
observations are new, but the same test cases had been used under harness v1; because v3 analysis
informed the treatment correction, v4 is corrective rather than an independent confirmation.

The experiment estimates benchmark performance under a controlled synthetic enterprise-support
setting. It does **not** estimate production incident prevalence or prove that governance is superior
for every system, task, or deployment.
