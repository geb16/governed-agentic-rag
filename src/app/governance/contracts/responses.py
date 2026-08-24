"""Define stable HTTP-facing views of governed workflow state.

Responses expose decisions, evidence identities, bounded usage, and audit counts
without leaking provider conversation objects or persistence rows.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.baseline.application.contracts import ToolCallRecord, Usage
from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceReference
from app.governance.contracts.decisions import ApprovalRecord, ApprovalRoute, RiskAssessment
from app.governance.contracts.enums import WorkflowStage, WorkflowStatus
from app.governance.contracts.execution import RecoveryResult
from app.governance.contracts.tasks import ClassificationResult, ProposedAction


class GovernedResponse(StrictModel):
    """Return the complete caller-visible state of a governed workflow.

    Optional stage outputs remain absent until produced. The response includes
    evidence hashes and audit metadata for traceability but excludes raw internal
    checkpoints and trusted security configuration.
    """

    workflow_id: str
    request_id: str
    case_id: str
    trace_id: str
    status: WorkflowStatus
    current_stage: WorkflowStage
    state_version: int
    answer: str | None = None
    classification: ClassificationResult | None = None
    proposal: ProposedAction | None = None
    risk: RiskAssessment | None = None
    approval_route: ApprovalRoute | None = None
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    recovery: RecoveryResult | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    retrieval_backend: str
    model: str
    usage: Usage = Field(default_factory=Usage)
    audit_event_count: int = Field(ge=0)
    error_code: str | None = None
    created_at: datetime


class WorkflowSummary(StrictModel):
    """Return a compact workflow view suitable for polling and approval clients.

    The summary contains the proposal digest and pending roles needed to make a
    concurrency-safe approval decision without returning the full workflow state.
    """

    workflow_id: str
    request_id: str
    status: WorkflowStatus
    current_stage: WorkflowStage
    state_version: int
    proposal_digest: str | None = None
    pending_roles: list[str] = Field(default_factory=list)
