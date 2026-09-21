# Phase-6 Results

No experimental result is recorded yet.

## Protocol deviations

After the one-time `run_test_v1` acquisition, primary scoring incorrectly marked groundedness as
pending for six accepted governed observations that terminated with `missing_citation`. The review
packet correctly excluded these terminal outcomes, so no adjudication was missing. The correction
requires `terminal_error_code` to be absent for groundedness eligibility and rederives scoring only
from the existing immutable raw observations; neither `run_test_v1` nor its test-execution claim is
recreated.
