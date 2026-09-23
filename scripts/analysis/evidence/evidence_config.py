"""Define immutable identities and labels for the Phase 7 evidence pipeline."""

from __future__ import annotations

from typing import Literal

RELEASE_VERSION = "v2"
RELEASE_ID = f"paired-agent-evaluation-{RELEASE_VERSION}"
RELEASE_SHA256 = "9c8ff4a069535be78c1b76e99e28d9f71255d03ff9bec802c40fdf0b8853115b"

GENERATED_FILENAMES = (
    "figure-1-overall-effects.svg",
    "figure-2-condition-estimates.svg",
    "figure-3-operational-indicators.svg",
    "metric-denominators.csv",
    "observed-routes.csv",
    "operational-summary.csv",
    "overall-results.csv",
    "stratified-paired-effects.csv",
    "terminal-errors.csv",
)

METRIC_LABELS = {
    "appropriate_route_rate": "Appropriate route",
    "workflow_completion_rate": "Workflow completion",
    "action_correctness_rate": "Action correctness",
    "unsafe_action_prevention_rate": "Unsafe-action prevention",
    "approval_control_accuracy": "Approval control",
    "escalation_recall": "Escalation recall",
    "escalation_precision": "Escalation precision",
    "escalation_f1": "Escalation F1",
    "false_escalation_rate": "False escalation",
    "recovery_success_rate": "Recovery success",
    "safe_termination_rate": "Safe termination",
    "groundedness_rate": "Groundedness",
    "context_precision": "Context precision",
    "audit_trace_completeness": "Audit completeness",
}

MetricDirection = Literal["higher", "lower"]

# Explicit directions make figure semantics fail closed when a metric is added.
METRIC_DIRECTIONS: dict[str, MetricDirection] = {
    "appropriate_route_rate": "higher",
    "workflow_completion_rate": "higher",
    "action_correctness_rate": "higher",
    "unsafe_action_prevention_rate": "higher",
    "approval_control_accuracy": "higher",
    "escalation_recall": "higher",
    "escalation_precision": "higher",
    "escalation_f1": "higher",
    "false_escalation_rate": "lower",
    "recovery_success_rate": "higher",
    "safe_termination_rate": "higher",
    "groundedness_rate": "higher",
    "context_precision": "higher",
    "audit_trace_completeness": "higher",
}

if METRIC_DIRECTIONS.keys() != METRIC_LABELS.keys():
    raise RuntimeError("Metric labels and directions must describe the same metrics")
