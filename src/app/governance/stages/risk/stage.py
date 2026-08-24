"""Implement stage four: deterministic, explainable risk assessment.

Rules combine classification confidence, security findings, proposal validation,
tool category, business thresholds, and sensitivity. The model supplies candidate
data but never assigns risk, approval roles, clarification, or denial.
"""

from __future__ import annotations

from app.governance.contracts import (
    ClassificationResult,
    ProposedAction,
    ProposedActionKind,
    RiskAssessment,
    RiskLevel,
    Sensitivity,
    TaskIntent,
    TaskType,
)
from app.governance.stages.risk.builder import AssessmentBuilder
from app.governance.stages.risk.policy import DEFAULT_RISK_POLICY, RiskPolicy
from app.governance.stages.risk.tool_rules import assess_tool


class RiskCheckingStage:
    """Apply versioned deterministic controls to a model-generated proposal.

    Args:
        policy: Immutable risk thresholds and scores; defaults to the reviewed policy.
    """

    def __init__(self, policy: RiskPolicy = DEFAULT_RISK_POLICY) -> None:
        """Initialize assessment with an immutable versioned policy."""
        self._policy = policy

    def run(
        self,
        classification: ClassificationResult,
        proposal: ProposedAction | None,
    ) -> RiskAssessment:
        """Evaluate classification, proposal, tool, and sensitivity controls.

        Args:
            classification: Validated stage-one classification.
            proposal: Validated stage-three proposal, or ``None`` on planning failure.

        Returns:
            Explainable assessment with routing signals and required roles.
        """
        builder = AssessmentBuilder(self._policy)
        self._assess_classification(builder, classification)
        if proposal is None:
            builder.add(
                "proposal_unavailable",
                RiskLevel.CRITICAL,
                "No candidate action is available for evaluation.",
                mappings=["separate-decision-execution"],
            )
            builder.deny = True
            return builder.build()

        self._assess_proposal(builder, classification, proposal)
        if proposal.kind == ProposedActionKind.TOOL:
            assess_tool(builder, proposal)
        else:
            builder.add(
                "response_only",
                RiskLevel.LOW,
                "The proposal has no tool side effect.",
                mappings=["least-agency"],
            )
        self._assess_sensitivity(builder, classification, proposal)
        return builder.build()

    def _assess_classification(
        self,
        builder: AssessmentBuilder,
        classification: ClassificationResult,
    ) -> None:
        """Apply security, completeness, and confidence rules to classification."""
        if classification.security_category:
            builder.add(
                "untrusted_instruction_attack",
                RiskLevel.CRITICAL,
                "The request was blocked by deterministic prompt-security screening.",
                mappings=["OWASP-Agentic-ASI01", "NIST-AI-600-1"],
            )
            builder.deny = True
        if classification.missing_information:
            builder.add(
                "classification_missing_information",
                RiskLevel.HIGH,
                "Required request information is missing.",
                mappings=["human-oversight", "fail-safe-default"],
            )
            builder.clarify = True
        if classification.confidence < self._policy.confidence_threshold:
            builder.add(
                "low_classification_confidence",
                RiskLevel.HIGH,
                "Task classification confidence is below the automatic threshold.",
                mappings=["human-oversight"],
            )
            builder.require("support_manager")

    def _assess_proposal(
        self,
        builder: AssessmentBuilder,
        classification: ClassificationResult,
        proposal: ProposedAction,
    ) -> None:
        """Apply validation, confidence, capability, and task-alignment rules."""
        if proposal.validation_error:
            level = (
                RiskLevel.CRITICAL
                if proposal.validation_error == "tool_not_allowlisted"
                else RiskLevel.HIGH
            )
            builder.add(
                proposal.validation_error,
                level,
                "The candidate action failed allowlist or schema validation.",
                mappings=["OWASP-Agentic-ASI02", "least-agency"],
            )
            builder.deny = proposal.validation_error == "tool_not_allowlisted"
            builder.clarify = not builder.deny
        if proposal.missing_information:
            builder.add(
                "proposal_missing_information",
                RiskLevel.HIGH,
                "The proposed action identifies required parameters that are missing.",
                mappings=["fail-safe-default"],
            )
            builder.clarify = True
        if proposal.confidence < self._policy.confidence_threshold:
            builder.add(
                "low_proposal_confidence",
                RiskLevel.HIGH,
                "Candidate-action confidence is below the automatic threshold.",
                mappings=["human-oversight"],
            )
            builder.require("support_manager")
        if classification.intent == TaskIntent.DATA_DELETION:
            builder.add(
                "unsupported_data_deletion",
                RiskLevel.CRITICAL,
                "Data deletion is not an allowlisted simulated capability.",
                policy_reference="kb-data-governance",
                mappings=["OWASP-Agentic-ASI02", "least-agency"],
            )
            builder.deny = True
        if (
            classification.task_type == TaskType.STATE_CHANGING
            and proposal.kind == ProposedActionKind.RESPOND
        ):
            builder.add(
                "requested_action_not_proposed",
                RiskLevel.HIGH,
                "A state-changing request has no validated candidate tool action.",
                mappings=["separate-decision-execution"],
            )
            builder.clarify = True

    @staticmethod
    def _assess_sensitivity(
        builder: AssessmentBuilder,
        classification: ClassificationResult,
        proposal: ProposedAction,
    ) -> None:
        """Require accountable oversight for non-denied sensitive actions."""
        if (
            classification.sensitivity in {Sensitivity.HIGH, Sensitivity.CRITICAL}
            and not builder.deny
            and proposal.tool_name != "request_human_review"
        ):
            builder.add(
                "sensitive_task",
                RiskLevel.HIGH,
                "Sensitive tasks require accountable human oversight.",
                mappings=["NIST-AI-600-1", "human-oversight"],
            )
            builder.require("support_manager")
