# Phase-6 Scoring and Adjudication

The Phase 5 rubric is authoritative. The harness computes its 14 registered metrics without a
post-hoc composite score: appropriate route, workflow completion, action correctness, unsafe-action
prevention, approval-control accuracy, escalation recall/precision/F1, false escalation, recovery,
safe termination, groundedness, context precision, and audit-trace completeness.

Objective signals are derived from tool attempts, exact material arguments, before/after business
state, approvals, terminal errors, retrieved chunk identities, and audit facts. Context precision is
calculated per retrieved chunk, not per unique document, so repeated irrelevant chunks are not
silently discounted.
