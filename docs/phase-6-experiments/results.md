# Phase-6 Results

The canonical Phase 6 results are sealed under
[`data/evaluation/paired_agent_evaluation/v3/`](../../data/evaluation/paired_agent_evaluation/v3/).
The [HTML report](../../data/evaluation/paired_agent_evaluation/v3/report.html) presents the final
primary estimates, paired differences, confidence intervals, and secondary Ragas grades. The
release identity is `paired-agent-evaluation-v3`, with aggregate SHA-256
`0f2c281ab19ea6a1c44bf75ad79266c1d51e9a88ee82cd8ea01850561bc7110e`. Releases v1 and v2
remain unchanged as superseded audit history.

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
[v2 correction record](../../data/evaluation/paired_agent_evaluation/v2/correction.json)
binds v2 to v1 and lists every changed derived artifact. Raw observations, the review packet,
resolved human adjudications, secondary Ragas grades, schedule, and test-execution claim are
unchanged.

A second audit found that route inference gave a later final-answer safety block precedence over a
baseline `request_human_review` tool call that had already succeeded. Corrective release v3 applies
the frozen route definition—successful review request with no business action—while retaining the
terminal citation error independently. Its
[correction record](../../data/evaluation/paired_agent_evaluation/v3/correction.json) binds v3 to v2.
Only normalization-dependent outputs changed; raw observations, review packet, resolved human
adjudications, Ragas grades, schedule, and test-execution claim remain byte-for-byte unchanged.

The corrected escalation results are baseline recall 27/33 (0.818), precision 27/50 (0.540), and
false-escalation rate 23/207 (0.111), compared with governed recall 0/33, precision 0/4, and
false-escalation rate 4/207 (0.019). The governed-minus-baseline false-escalation effect is
`−0.092 [−0.172, −0.020]`; lower is better. Governed recall zero and its four false escalations are
observed workflow outcomes, not normalization defects, and remain reported for future system work.
