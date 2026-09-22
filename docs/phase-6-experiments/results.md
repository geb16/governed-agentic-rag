# Phase-6 Results

The canonical Phase 6 results are sealed under
[`data/evaluation/paired_agent_evaluation/v1/`](../../data/evaluation/paired_agent_evaluation/v1/).
The [HTML report](../../data/evaluation/paired_agent_evaluation/v1/report.html) presents the final
primary estimates, paired differences, confidence intervals, and secondary Ragas grades. The
release identity is `paired-agent-evaluation-v1`, with aggregate SHA-256
`150be865736eb274751ddec24f0a084e2d2942c119a25e164600907f492165ea`.

## Protocol deviations

After the one-time `run_test_v1` acquisition, primary scoring incorrectly marked groundedness as
pending for six accepted governed observations that terminated with `missing_citation`. The review
packet correctly excluded these terminal outcomes, so no adjudication was missing. The correction
requires `terminal_error_code` to be absent for groundedness eligibility and rederives scoring only
from the existing immutable raw observations; neither `run_test_v1` nor its test-execution claim is
recreated.
