# Immutable identities and labels used by the Phase-7 evidence pipeline.

from __future__ import annotations

RELEASE_ID = "paired-agent-evaluation-v1"
RELEASE_SHA256 = "150be865736eb274751ddec24f0a084e2d2942c119a25e164600907f492165ea"

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
