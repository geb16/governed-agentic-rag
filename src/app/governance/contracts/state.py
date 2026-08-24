"""Define the provider-neutral durable aggregate for one governed invocation.

The aggregate checkpoints each stage, decisions, usage, and terminal outcome.
Optimistic concurrency uses ``state_version``; persistence adapters serialize this
model without adding database-specific behavior to the domain contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import Field

from app.baseline.application.contracts import ToolCallRecord, Usage
from app.domain.contracts import StrictModel
from app.governance.contracts.decisions import ApprovalRecord, ApprovalRoute, RiskAssessment
from app.governance.contracts.enums import WorkflowStage, WorkflowStatus
from app.governance.contracts.execution import GovernedFinalDraft, RecoveryResult
from app.governance.contracts.tasks import (
    ClassificationResult,
    GovernedRequest,
    ProposedAction,
    RetrievalResult,
)


class WorkflowState(StrictModel):
    """Hold the complete durable state of one seven-stage workflow.

    New workflows receive unique workflow and trace identities. Stage outputs are
    populated monotonically as orchestration advances, and terminal errors use a
    stable ``error_code`` rather than provider exception text.
    """

    schema_version: int = 1
    workflow_id: str = Field(
        default_factory=lambda: f"wf_{uuid4().hex}",
        pattern=r"^wf_[a-zA-Z0-9_-]+$",
    )
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex}")
    request: GovernedRequest
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    current_stage: WorkflowStage = WorkflowStage.TASK_CLASSIFICATION
    state_version: int = 1
    classification: ClassificationResult | None = None
    retrieval: RetrievalResult | None = None
    proposal: ProposedAction | None = None
    risk: RiskAssessment | None = None
    approval_route: ApprovalRoute | None = None
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    recovery: RecoveryResult | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    final: GovernedFinalDraft | None = None
    usage: Usage = Field(default_factory=Usage)
    error_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
