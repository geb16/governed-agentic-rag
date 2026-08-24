"""Declare immutable thresholds and scores for Phase 4 governance policy.

Policy identity is included in audit events and experiment manifests. Thresholds use
minor currency units to avoid floating-point ambiguity.
"""

from dataclasses import dataclass, field

from app.governance.contracts import RiskLevel

GOVERNANCE_POLICY_VERSION = "phase4-governance-policy-v1"


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Configure deterministic confidence, approval, and severity thresholds.

    Attributes:
        version: Stable policy identity recorded for reproducibility.
        confidence_threshold: Minimum model confidence for automatic routing.
        refund_approval_minor: Finance-review threshold in minor currency units.
        refund_dual_approval_minor: Dual-control threshold in minor currency units.
        scores: Normalized numeric score assigned to each risk level.
    """

    version: str = GOVERNANCE_POLICY_VERSION
    confidence_threshold: float = 0.65
    refund_approval_minor: int = 50_000
    refund_dual_approval_minor: int = 500_000
    scores: dict[RiskLevel, int] = field(
        default_factory=lambda: {
            RiskLevel.LOW: 20,
            RiskLevel.MEDIUM: 45,
            RiskLevel.HIGH: 75,
            RiskLevel.CRITICAL: 100,
        }
    )


DEFAULT_RISK_POLICY = RiskPolicy()
RISK_RANK = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}
