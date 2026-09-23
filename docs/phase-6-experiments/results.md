# Phase-6 Results

The canonical Phase 6 results are sealed under
[`data/evaluation/paired_agent_evaluation/v2/`](../../data/evaluation/paired_agent_evaluation/v2/).
The [HTML report](../../data/evaluation/paired_agent_evaluation/v2/report.html) presents the final
primary estimates, paired differences, confidence intervals, and secondary Ragas grades. The
release identity is `paired-agent-evaluation-v2`, with aggregate SHA-256
`9c8ff4a069535be78c1b76e99e28d9f71255d03ff9bec802c40fdf0b8853115b`. The original
`paired-agent-evaluation-v1` release remains unchanged as superseded audit history.

## Corrected recovery result

The corrected recovery-success counts are 3/24 for baseline and 11/24 for governance, corresponding
to rates of 0.125 and 0.458. The governed-minus-baseline paired effect is `+0.333` with a 95%
confidence interval of `[-0.167, 0.778]`. The interval crosses zero, so this pilot does not establish
a statistically conclusive recovery advantage even though its point estimate favours governance.

## Protocol deviations

After the one-time `run_test_v1` acquisition, primary scoring incorrectly marked groundedness as
pending for six accepted governed observations that terminated with `missing_citation`. The review
packet correctly excluded these terminal outcomes, so no adjudication was missing. The correction
requires `terminal_error_code` to be absent for groundedness eligibility and rederives scoring only
from the existing immutable raw observations; neither `run_test_v1` nor its test-execution claim is
recreated.

Subsequent audit found that baseline safety blocks carrying `fabricated_citation` were not projected
into `terminal_error_code`. Thirteen such terminal outcomes were therefore incorrectly eligible for
recovery success, while equivalent governed terminal outcomes were excluded. Corrective release v2
maps baseline safety blocks into the shared terminal-error field and re-derives normalization and
primary scoring symmetrically. The
[canonical correction record](../../data/evaluation/paired_agent_evaluation/v2/correction.json)
binds v2 to v1 and lists every changed derived artifact. Raw observations, the review packet,
resolved human adjudications, secondary Ragas grades, schedule, and test-execution claim are
unchanged.
