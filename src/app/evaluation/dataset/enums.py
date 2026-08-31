"""Stable serialized vocabulary for the Phase 5 evaluation dataset."""

from enum import StrEnum


class DatasetSplit(StrEnum):
    """Separate rubric validation from the final comparative test set."""

    VALIDATION = "validation"
    TEST = "test"


class ScenarioCategory(StrEnum):
    """Primary mutually exclusive benchmark stratum."""

    NORMAL = "normal"
    AMBIGUOUS = "ambiguous"
    POLICY_SENSITIVE = "policy_sensitive"
    HIGH_RISK = "high_risk"
    MISSING_INFORMATION = "missing_information"
    TOOL_FAILURE = "tool_failure"


class InteractionChannel(StrEnum):
    """Synthetic enterprise request channel."""

    CHAT = "chat"
    EMAIL = "email"
    PORTAL = "portal"
    API = "api"


class ExpectedRoute(StrEnum):
    """Governance-neutral intended handling observable in either condition."""

    ANSWER = "answer"
    EXECUTE = "execute"
    HUMAN_REVIEW = "human_review"
    CLARIFY = "clarify"
    DENY = "deny"
    SAFE_TERMINATE = "safe_terminate"


class ExpectedTaskType(StrEnum):
    """Operational effect expected from a synthetic request."""

    READ_ONLY = "read_only"
    STATE_CHANGING = "state_changing"
    ESCALATION = "escalation"
    UNSUPPORTED = "unsupported"


class ExpectedSensitivity(StrEnum):
    """Information sensitivity assigned by the gold label."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ExpectedRiskLevel(StrEnum):
    """Risk severity expected from policy-aware classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewDecision(StrEnum):
    """Deterministic human decision replayed by the evaluation harness."""

    APPROVE = "approve"
    REJECT = "reject"


class RecoveryExpectation(StrEnum):
    """Expected terminal behavior for an injected tool failure."""

    NOT_APPLICABLE = "not_applicable"
    RETRIED_AND_SUCCEEDED = "retried_and_succeeded"
    SAFE_TERMINATION = "safe_termination"


class TraceFact(StrEnum):
    """Semantic evidence required for audit-trace completeness scoring."""

    REQUEST_IDENTITY = "request_identity"
    CLASSIFICATION = "classification"
    RETRIEVAL_EVIDENCE = "retrieval_evidence"
    PROPOSED_ACTION = "proposed_action"
    RISK_DECISION = "risk_decision"
    APPROVAL_ROUTE = "approval_route"
    APPROVAL_DECISION = "approval_decision"
    TOOL_ATTEMPT = "tool_attempt"
    RECOVERY_DECISION = "recovery_decision"
    FINAL_OUTCOME = "final_outcome"
