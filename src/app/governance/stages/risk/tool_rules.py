"""Apply capability-specific risk and approval rules to validated tools.

Unknown tools fail closed. Read-only and human-escalation tools remain low risk;
synthetic mutations receive policy-specific thresholds and role requirements.
"""

from __future__ import annotations

from app.governance.contracts import ProposedAction, RiskLevel
from app.governance.stages.risk.builder import AssessmentBuilder

_READ_ONLY_TOOLS = {"policy_lookup", "ticket_lookup", "response_drafter"}


def assess_tool(builder: AssessmentBuilder, proposal: ProposedAction) -> None:
    """Add deterministic findings for an allowlisted tool proposal.

    Args:
        builder: Active assessment accumulator.
        proposal: Catalog-validated tool proposal.
    """
    name = proposal.tool_name
    if name in _READ_ONLY_TOOLS:
        builder.add(
            "read_only_tool",
            RiskLevel.LOW,
            "The allowlisted tool has no enterprise state side effect.",
            mappings=["least-agency"],
        )
    elif name == "request_human_review":
        builder.add(
            "safe_human_escalation",
            RiskLevel.LOW,
            "The tool creates a simulated review request and does not approve an action.",
            mappings=["human-oversight", "interruptibility"],
        )
    elif name == "update_ticket_status":
        builder.add(
            "bounded_ticket_update",
            RiskLevel.MEDIUM,
            "The tool changes only isolated synthetic ticket state.",
            policy_reference="kb-support-sop",
            mappings=["least-agency", "parameter-validation"],
        )
    elif name == "issue_refund":
        _assess_refund(builder, proposal)
    elif name == "change_access_role":
        _assess_access_change(builder, proposal)
    else:
        builder.add(
            "unknown_tool_risk",
            RiskLevel.CRITICAL,
            "The tool has no governance policy rule.",
            mappings=["deny-by-default"],
        )
        builder.deny = True


def _assess_refund(builder: AssessmentBuilder, proposal: ProposedAction) -> None:
    """Apply finance and dual-control thresholds to a validated refund amount."""
    amount_minor = proposal.validated_arguments.get("amount_minor")
    if not isinstance(amount_minor, int):
        builder.add(
            "refund_amount_missing",
            RiskLevel.HIGH,
            "A validated refund amount is required.",
            policy_reference="kb-refund-policy",
        )
        builder.clarify = True
    elif amount_minor >= builder.policy.refund_dual_approval_minor:
        builder.add(
            "large_refund",
            RiskLevel.CRITICAL,
            "Refunds of 5,000 currency units or more require finance and fraud review.",
            policy_reference="kb-refund-policy",
            mappings=["human-oversight", "dual-control"],
        )
        builder.require("finance_manager")
        builder.require("fraud_reviewer")
    elif amount_minor >= builder.policy.refund_approval_minor:
        builder.add(
            "approval_threshold_refund",
            RiskLevel.HIGH,
            "Refunds of 500 currency units or more require finance approval.",
            policy_reference="kb-refund-policy",
            mappings=["human-oversight"],
        )
        builder.require("finance_manager")
    else:
        builder.add(
            "bounded_refund",
            RiskLevel.MEDIUM,
            "The refund is below the documented human-approval threshold.",
            policy_reference="kb-refund-policy",
            mappings=["parameter-validation"],
        )


def _assess_access_change(
    builder: AssessmentBuilder,
    proposal: ProposedAction,
) -> None:
    """Require IAM oversight and elevate administrator assignments to critical."""
    privileged = str(proposal.validated_arguments.get("new_role", "")).lower()
    level = RiskLevel.CRITICAL if privileged == "administrator" else RiskLevel.HIGH
    builder.add(
        "privileged_access_change" if privileged == "administrator" else "access_role_change",
        level,
        (
            "Privileged access requires IAM administrator approval."
            if privileged == "administrator"
            else "Access-role changes require IAM oversight."
        ),
        policy_reference="kb-iam-policy",
        mappings=(
            ["OWASP-Agentic-ASI02", "human-oversight"]
            if privileged == "administrator"
            else ["least-privilege", "human-oversight"]
        ),
    )
    builder.require("iam_administrator")
