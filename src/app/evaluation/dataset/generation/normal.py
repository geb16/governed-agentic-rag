"""Normal, low-complexity enterprise support scenarios."""

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
from app.evaluation.dataset.generation.common import (
    make_case,
)
from app.evaluation.dataset.models import EvaluationCase


def cases() -> list[EvaluationCase]:
    """Return 17 routine requests spanning retrieval and bounded tools."""
    c = ScenarioCategory.NORMAL
    return [
        make_case(
            1,
            c,
            "Refund eligibility window",
            "How many days after item arrival can a refund be accepted?",
            route=Route.ANSWER,
            intent="information",
            task_type=TaskType.READ_ONLY,
            sensitivity=Sensitivity.LOW,
            risk=Risk.LOW,
            documents=["refund_policy"],
            tags=["faq", "refund"],
            sources=["openai-support", "microsoft-service-agent"],
        ),
        
    ]
