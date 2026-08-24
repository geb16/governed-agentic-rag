"""Accumulate explainable findings into one deterministic risk assessment."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.governance.contracts import RiskAssessment, RiskFlag, RiskLevel
from app.governance.stages.risk.policy import RISK_RANK, RiskPolicy


@dataclass(slots=True)
class AssessmentBuilder:
    """Collect risk flags, roles, and terminal signals under one policy version.

    Attributes:
        policy: Immutable thresholds and score mapping used by the assessment.
        flags: Ordered explainable findings accumulated by policy rules.
        required_roles: Deduplicated human roles required before execution.
        deny: Whether policy requires terminal denial.
        clarify: Whether missing or invalid information requires clarification.
    """

    policy: RiskPolicy
    flags: list[RiskFlag] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    deny: bool = False
    clarify: bool = False

    def add(
        self,
        code: str,
        level: RiskLevel,
        explanation: str,
        *,
        policy_reference: str | None = None,
        mappings: list[str] | None = None,
    ) -> None:
        """Append one explainable and control-mapped risk finding.

        Args:
            code: Stable machine-readable finding identity.
            level: Severity contributed by the finding.
            explanation: Bounded human-readable reason.
            policy_reference: Optional knowledge or policy identity.
            mappings: Optional external or architectural control mappings.
        """
        self.flags.append(
            RiskFlag(
                code=code,
                level=level,
                explanation=explanation,
                policy_reference=policy_reference,
                control_mapping=mappings or [],
            )
        )

    def require(self, role: str) -> None:
        """Add a required approval role once while preserving stable order."""
        if role not in self.required_roles:
            self.required_roles.append(role)

    def build(self) -> RiskAssessment:
        """Build the final assessment from the highest-severity finding.

        Returns:
            Versioned assessment containing score, findings, roles, and routing signals.
        """
        level = max(
            (flag.level for flag in self.flags),
            key=RISK_RANK.__getitem__,
            default=RiskLevel.LOW,
        )
        return RiskAssessment(
            level=level,
            score=self.policy.scores[level],
            flags=self.flags,
            required_roles=self.required_roles,
            deny=self.deny,
            requires_clarification=self.clarify,
            policy_version=self.policy.version,
        )
