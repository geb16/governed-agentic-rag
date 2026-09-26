"""Expose harness freezing and test-authorization controls."""

from paired_agent_evaluation.experiment_control.authorization import claim_test_execution
from paired_agent_evaluation.experiment_control.freeze import (
    verify_harness_freeze,
    write_harness_freeze,
)
from paired_agent_evaluation.experiment_control.policy import harness_freeze_id
from paired_agent_evaluation.experiment_control.readiness import verify_harness_readiness

__all__ = [
    "claim_test_execution",
    "harness_freeze_id",
    "verify_harness_freeze",
    "verify_harness_readiness",
    "write_harness_freeze",
]
