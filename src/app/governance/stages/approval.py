"""Implement stage five: deterministic approval routing.

The stage binds every route to the exact proposal digest. Models cannot approve
their own actions; policy outcomes determine automatic continuation, clarification,
denial, or expiring role-bound human review.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.governance.contracts import (
    ApprovalDecision,
    ApprovalRoute,
    ProposedAction,
    RiskAssessment,
    RiskLevel,
)
from app.governance.security.digests import proposal_digest

APPROVAL_TTL = timedelta(hours=24)


class ApprovalRoutingStage:
    """Select a deterministic route without granting the model approval authority."""

    def run(
        self,
        risk: RiskAssessment,
        proposal: ProposedAction | None,
    ) -> ApprovalRoute:
        """Bind a routing decision to the assessed proposal.

        Args:
            risk: Deterministic risk assessment and required roles.
            proposal: Validated proposal, or ``None`` when planning failed closed.

        Returns:
            A digest-bound route. Human routes expire after ``APPROVAL_TTL``.
        """
        digest = proposal_digest(
            proposal.model_dump(mode="json") if proposal else {"proposal": None}
        )
        if risk.deny:
            return ApprovalRoute(
                decision=ApprovalDecision.DENY,
                rationale="A deny-by-default governance rule was triggered.",
                proposal_digest=digest,
            )
        if risk.requires_clarification:
            return ApprovalRoute(
                decision=ApprovalDecision.REQUEST_CLARIFICATION,
                rationale="Required information or valid action parameters are missing.",
                proposal_digest=digest,
            )
        roles = list(risk.required_roles)
        if risk.level in {RiskLevel.HIGH, RiskLevel.CRITICAL} and not roles:
            roles.append("support_manager")
        if roles:
            return ApprovalRoute(
                decision=ApprovalDecision.REQUIRE_HUMAN,
                required_roles=roles,
                rationale="Policy-bound human approval is required before execution.",
                proposal_digest=digest,
                expires_at=datetime.now(UTC) + APPROVAL_TTL,
            )
        return ApprovalRoute(
            decision=ApprovalDecision.AUTO_CONTINUE,
            rationale="The action is within documented automatic-control thresholds.",
            proposal_digest=digest,
        )
