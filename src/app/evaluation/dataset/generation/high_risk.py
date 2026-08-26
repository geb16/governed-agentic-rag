# High-impact actions and security attacks with fail-safe gold outcomes.


from typing import Any

from app.evaluation.dataset.enums import (
    ExpectedRiskLevel as Risk,
)
from app.evaluation.dataset.enums import (
    ExpectedRoute as Route,
)
from app.evaluation.dataset.enums import (
    ExpectedSensitivity as Sensitivity,
)
from app.evaluation.dataset.enums import (
    ExpectedTaskType as TaskType,
)
from app.evaluation.dataset.enums import (
    ScenarioCategory,
)
from app.evaluation.dataset.models import EvaluationCase


def cases() -> list[EvaluationCase]:
    """Return 17 high-risk cases emphasizing unsafe-action prevention."""
    c = ScenarioCategory.HIGH_RISK
    attack: dict[str, Any] = {
        "route": Route.DENY,
        "intent": "security_attack",
        "task_type": TaskType.UNSUPPORTED,
        "sensitivity": Sensitivity.CRITICAL,
        "risk": Risk.CRITICAL,
        "denial_code": "untrusted_instruction_attack",
        "risk_flags": ["untrusted_instruction_attack"],
        "sources": ["owasp-agentic-top10", "owasp-excessive-agency"],
    }
    return [
  
    ]
