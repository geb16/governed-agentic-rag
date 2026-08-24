"""Controlled creation of synthetic human-review requests."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.actions import ActionResultStatus, ControlledToolResult
from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceType
from app.domain.repositories import SyntheticRepository
from app.domain.tasks import ToolExecutionContext
from app.tools.evidence import evidence_reference


class HumanReviewArguments(StrictModel):
    """Validated reason, role, ticket, and idempotency key for review."""

    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    reason: str = Field(min_length=10, max_length=500)
    requested_role: Literal[
        "support_supervisor",
        "finance_manager",
        "iam_manager",
        "privacy_officer",
    ]
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,100}$")


class HumanReviewResult(ControlledToolResult):
    """Synthetic escalation identity and pending-review state."""

    escalation_id: str | None = None
    ticket_id: str
    requested_role: str
    status: str


class HumanReviewTool:
    """Create a review record without implementing an approval workflow."""

    name = "request_human_review"
    description = (
        "Create a pending human-review request in the isolated synthetic support system. "
        "The baseline LLM may select this tool when policy, missing information, sensitivity, "
        "or uncertainty warrants escalation. This is not a formal approval router."
    )
    input_model = HumanReviewArguments

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def execute(
        self,
        arguments: HumanReviewArguments,
        context: ToolExecutionContext,
    ) -> HumanReviewResult:
        """Create or return an idempotent review in the trusted case context."""
        record, changed = self._repository.request_human_review(
            context.case_id,
            arguments.ticket_id,
            arguments.reason,
            arguments.requested_role,
            arguments.idempotency_key,
        )
        if record is None:
            return HumanReviewResult(
                message="The synthetic ticket was not found; no review was requested.",
                outcome_status=ActionResultStatus.NO_CHANGE,
                ticket_id=arguments.ticket_id,
                requested_role=arguments.requested_role,
                status="not_found",
            )
        payload = record.model_dump(mode="json")
        return HumanReviewResult(
            message=(
                "A pending human-review request was created."
                if changed
                else "The existing human-review request was returned for this idempotency key."
            ),
            state_changed=changed,
            outcome_status=(
                ActionResultStatus.EXECUTED if changed else ActionResultStatus.NO_CHANGE
            ),
            escalation_id=record.escalation_id,
            ticket_id=record.ticket_id,
            requested_role=record.requested_role,
            status=record.status,
            evidence=[
                evidence_reference(
                    evidence_id=f"escalation:{context.case_id}:{record.escalation_id}",
                    evidence_type=EvidenceType.BUSINESS_RECORD,
                    source_id=record.escalation_id,
                    title=f"Synthetic human review {record.escalation_id}",
                    payload=payload,
                )
            ],
        )
