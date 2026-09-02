from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import Field

from app.domain.contracts import StrictModel

AUDIT_SCHEMA_VERSION = 2


class AuditStage(StrEnum):
    """Stable audit vocabulary for the governed workflow stages."""

    TASK_CLASSIFICATION = "task_classification"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    PROPOSED_ACTION_GENERATION = "proposed_action_generation"
    RISK_CHECKING = "risk_checking"
    APPROVAL_ROUTING = "approval_routing"
    RETRY_RECOVERY = "retry_recovery"
    FINAL_RESPONSE_AUDIT = "final_response_audit"


class AuditEventType(StrEnum):
    WORKFLOW_STARTED = "workflow_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    STAGE_SKIPPED = "stage_skipped"
    DECISION_RECORDED = "decision_recorded"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECORDED = "approval_recorded"
    APPROVAL_EXPIRED = "approval_expired"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    TOOL_ATTEMPTED = "tool_attempted"
    RETRY_SCHEDULED = "retry_scheduled"
    STAGE_FAILED = "stage_failed"
    WORKFLOW_COMPLETED = "workflow_completed"


class AuditActorType(StrEnum):
    SYSTEM = "system"
    MODEL = "model"
    TOOL = "tool"
    HUMAN = "human"


class AuditEvent(StrictModel):
    schema_version: int = AUDIT_SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    workflow_id: str
    trace_id: str
    sequence_number: int = Field(ge=1)
    stage: AuditStage
    event_type: AuditEventType
    actor_type: AuditActorType
    actor_id: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    input_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    output_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    details: dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    event_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class AuditTrace(StrictModel):
    workflow_id: str
    events: list[AuditEvent]
    chain_valid: bool
