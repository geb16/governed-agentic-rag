"""Verify deterministic counterbalancing of paired execution conditions."""

import hashlib

from paired_agent_evaluation.application.scheduling import condition_order
from paired_agent_evaluation.domain.executions import Condition


def test_condition_order_matches_frozen_digest_rule() -> None:
    """Alternate each case's seeded first condition across repetitions."""
    case_id = "case_eval_0001"
    expected_first = (
        (Condition.BASELINE, Condition.GOVERNED)
        if hashlib.sha256(f"20260831:{case_id}".encode()).digest()[0] % 2 == 0
        else (Condition.GOVERNED, Condition.BASELINE)
    )
    assert condition_order(case_id, 1, seed=20260831) == expected_first
    assert condition_order(case_id, 2, seed=20260831) == expected_first[::-1]
    assert condition_order(case_id, 3, seed=20260831) == expected_first
