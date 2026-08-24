"""Define validated risk and human-approval decision contracts.

The models in this module cross orchestration, persistence, audit, and HTTP
boundaries. Strict validation prevents untrusted caller data from supplying an
authenticated principal or bypassing proposal-digest and state-version checks.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.domain.contracts import StrictModel
from app.governance.contracts.enums import (
    ApprovalDecision,
    ApprovalStatus,
    RiskLevel,
)


class RiskFlag(StrictModel):
    """Describe one policy finding contributing to a risk assessment.

    The stable ``code`` supports evaluation, while ``explanation`` and optional
    mappings retain human-readable policy and control context.
    """

    code: str
    level: RiskLevel
    explanation: str = Field(min_length=1, max_length=500)
    policy_reference: str | None = None
    control_mapping: list[str] = Field(default_factory=list)


class RiskAssessment(StrictModel):
    """Capture the deterministic risk decision for one validated proposal.

    The bounded score and ordered flags explain the overall level. ``deny`` and
    ``requires_clarification`` are explicit terminal routing signals; required
    roles identify approvals that must be satisfied before execution.
    """

    level: RiskLevel
    score: int = Field(ge=0, le=100)
    flags: list[RiskFlag] = Field(default_factory=list)
    required_roles: list[str] = Field(default_factory=list)
    deny: bool = False
    requires_clarification: bool = False
    policy_version: str


class ApprovalRoute(StrictModel):
    """Bind an approval-routing decision to an immutable proposal digest.

    Expiration applies only to human approval routes. A resumed workflow must
    present approvals for the same digest so a changed proposal cannot reuse an
    earlier authorization.
    """

    decision: ApprovalDecision
    required_roles: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=500)
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expires_at: datetime | None = None


class ApprovalRecord(StrictModel):
    """Represent the durable status of one role-specific approval requirement.

    Actor identity is populated only after a trusted principal decides the
    record. Pending approvals therefore have no actor or decision timestamp.
    """

    approval_id: str
    role: str
    status: ApprovalStatus
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    actor_id: str | None = None
    comment: str | None = Field(default=None, max_length=500)
    decided_at: datetime | None = None


class ApprovalPrincipal(StrictModel):
    """Represent an authenticated subject and its trusted approval roles.

    The HTTP adapter constructs this model from server-side configuration; caller
    payloads cannot supply or override its subject or role bindings.
    """

    subject_id: str = Field(min_length=2, max_length=128)
    roles: frozenset[str] = Field(min_length=1)


class ApprovalCommand(StrictModel):
    """Carry an approval decision without accepting trusted identity attributes.

    The proposal digest prevents authorization of substituted work, while the
    expected state version supplies optimistic concurrency at the resume boundary.
    """

    role: str = Field(min_length=2, max_length=100)
    approved: bool
    proposal_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_state_version: int = Field(ge=1)
    comment: str | None = Field(default=None, max_length=500)
