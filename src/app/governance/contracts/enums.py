"""Declare stable serialized identities for workflow state and decisions.

Enum values are persisted and exposed over HTTP, so changing a value is a schema
and compatibility decision rather than a cosmetic rename.
"""

from enum import StrEnum


class WorkflowStage(StrEnum):
    """Identify each ordered stage of the governed workflow state machine."""

    TASK_CLASSIFICATION = "task_classification"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    PROPOSED_ACTION_GENERATION = "proposed_action_generation"
    RISK_CHECKING = "risk_checking"
    APPROVAL_ROUTING = "approval_routing"
    RETRY_RECOVERY = "retry_recovery"
    FINAL_RESPONSE_AUDIT = "final_response_audit"


# Canonical order used by orchestration, audit events, and evaluation.
STAGE_ORDER: tuple[WorkflowStage, ...] = tuple(WorkflowStage)


class WorkflowStatus(StrEnum):
    """Identify durable lifecycle states, including controlled terminal outcomes."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    CLARIFICATION_REQUIRED = "clarification_required"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskIntent(StrEnum):
    """Classify the business or security intent recognized by governance policy."""

    INFORMATION = "information"
    TICKET_LOOKUP = "ticket_lookup"
    TICKET_UPDATE = "ticket_update"
    REFUND = "refund"
    ACCESS_CHANGE = "access_change"
    HUMAN_ESCALATION = "human_escalation"
    DATA_DELETION = "data_deletion"
    SECURITY_ATTACK = "security_attack"
    OTHER = "other"


class TaskType(StrEnum):
    """Distinguish read-only, mutating, escalation, and unsupported work."""

    READ_ONLY = "read_only"
    STATE_CHANGING = "state_changing"
    ESCALATION = "escalation"
    UNSUPPORTED = "unsupported"


class Sensitivity(StrEnum):
    """Represent the information or operational sensitivity of a request."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ProposedActionKind(StrEnum):
    """Distinguish a response-only proposal from a simulated tool proposal."""

    RESPOND = "respond"
    TOOL = "tool"


class RiskLevel(StrEnum):
    """Represent the normalized severity assigned by deterministic risk policy."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalDecision(StrEnum):
    """Select automatic continuation, human review, clarification, or denial."""

    AUTO_CONTINUE = "auto_continue"
    REQUIRE_HUMAN = "require_human"
    REQUEST_CLARIFICATION = "request_clarification"
    DENY = "deny"


class ApprovalStatus(StrEnum):
    """Represent the lifecycle of one persisted role-bound approval."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RecoveryDisposition(StrEnum):
    """Summarize whether execution required recovery or terminated safely."""

    NOT_REQUIRED = "not_required"
    SUCCEEDED = "succeeded"
    RETRIED_AND_SUCCEEDED = "retried_and_succeeded"
    SAFE_TERMINATION = "safe_termination"
