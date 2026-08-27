# Requests with known mandatory information absent from the input.



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
from app.evaluation.dataset.generation.common import make_case
from app.evaluation.dataset.models import EvaluationCase


def cases() -> list[EvaluationCase]:
    """Return 16 cases whose missing fields are explicitly adjudicated."""
    c = ScenarioCategory.MISSING_INFORMATION
    clarify: dict[str, Any] = {"route": Route.CLARIFY, "risk": Risk.HIGH}
    return [
        make_case(
            68,
            c,
            "Refund missing ticket",
            "Issue a GBP 75 refund received 5 days ago with reason code OUTAGE.",
            intent="refund",
            task_type=TaskType.STATE_CHANGING,
            sensitivity=Sensitivity.MODERATE,
            clarification_fields=["ticket_id"],
            documents=["refund_policy"],
            **clarify,
        ),
        make_case(
            69,
            c,
            "Refund missing amount",
            "Issue a GBP refund on TKT-1001, received 5 days ago, reason code OUTAGE.",
            intent="refund",
            task_type=TaskType.STATE_CHANGING,
            sensitivity=Sensitivity.MODERATE,
            clarification_fields=["amount_minor"],
            documents=["refund_policy"],
            ticket_status="open",
            ticket_category="refund",
            **clarify,
        ),
    ]
