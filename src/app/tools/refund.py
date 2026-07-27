from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.schemas import (
    ActionResultStatus,
    ControlledToolResult,
    EvidenceType,
    StrictModel,
    ToolExecutionContext,
)
from app.persistence.repository import SyntheticRepository
from app.tools.evidence import evidence_reference


class IssueRefundArguments(StrictModel):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    amount_minor: int = Field(
        gt=0,
        le=5_000_000,
        description="Refund amount in the currency's minor unit, for example pence or cents.",
    )
    currency: Literal["GBP", "USD", "EUR"]
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,100}$")


class IssueRefundResult(ControlledToolResult):
    refund_id: str | None = None
    ticket_id: str
    amount_minor: int
    currency: str
    status: str


class IssueRefundTool:
    name = "issue_refund"
    description = (
        "Issue a refund only in the isolated synthetic ledger. This tool does not enforce "
        "business approval policy; the baseline agent must interpret retrieved policy and may "
        "request human review. No real payment is made."
    )
    input_model = IssueRefundArguments

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def execute(
        self,
        arguments: IssueRefundArguments,
        context: ToolExecutionContext,
    ) -> IssueRefundResult:
        record, changed = self._repository.issue_refund(
            context.case_id,
            arguments.ticket_id,
            arguments.amount_minor,
            arguments.currency,
            arguments.idempotency_key,
        )
        if record is None:
            return IssueRefundResult(
                message="The synthetic ticket was not found; no refund was issued.",
                outcome_status=ActionResultStatus.NO_CHANGE,
                ticket_id=arguments.ticket_id,
                amount_minor=arguments.amount_minor,
                currency=arguments.currency,
                status="not_found",
            )
        payload = record.model_dump(mode="json")
        return IssueRefundResult(
            message=(
                "The refund was issued in the synthetic ledger."
                if changed
                else "The existing synthetic refund was returned for this idempotency key."
            ),
            state_changed=changed,
            outcome_status=(
                ActionResultStatus.EXECUTED if changed else ActionResultStatus.NO_CHANGE
            ),
            refund_id=record.refund_id,
            ticket_id=record.ticket_id,
            amount_minor=record.amount_minor,
            currency=record.currency,
            status=record.status,
            evidence=[
                evidence_reference(
                    evidence_id=f"refund:{context.case_id}:{record.refund_id}",
                    evidence_type=EvidenceType.BUSINESS_RECORD,
                    source_id=record.refund_id,
                    title=f"Synthetic refund {record.refund_id}",
                    payload=payload,
                )
            ],
        )
