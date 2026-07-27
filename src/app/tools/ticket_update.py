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


class TicketUpdateArguments(StrictModel):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    new_status: Literal["open", "in_progress", "resolved", "closed"]


class TicketUpdateResult(ControlledToolResult):
    ticket_id: str
    status: str
    version: int | None = None


class TicketUpdateTool:
    name = "update_ticket_status"
    description = (
        "Change the status of a ticket inside the isolated synthetic case. "
        "This simulates a business-system write and has no external side effect."
    )
    input_model = TicketUpdateArguments

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def execute(
        self,
        arguments: TicketUpdateArguments,
        context: ToolExecutionContext,
    ) -> TicketUpdateResult:
        record, changed = self._repository.update_ticket_status(
            context.case_id,
            arguments.ticket_id,
            arguments.new_status,
        )
        if record is None:
            return TicketUpdateResult(
                message="The synthetic ticket was not found; no state changed.",
                outcome_status=ActionResultStatus.NO_CHANGE,
                ticket_id=arguments.ticket_id,
                status="not_found",
            )
        payload = record.model_dump(mode="json")
        return TicketUpdateResult(
            message=(
                "The synthetic ticket status was updated."
                if changed
                else "The synthetic ticket already had the requested status."
            ),
            state_changed=changed,
            outcome_status=(
                ActionResultStatus.EXECUTED if changed else ActionResultStatus.NO_CHANGE
            ),
            ticket_id=record.ticket_id,
            status=record.status,
            version=record.version,
            evidence=[
                evidence_reference(
                    evidence_id=(f"ticket:{context.case_id}:{record.ticket_id}:v{record.version}"),
                    evidence_type=EvidenceType.BUSINESS_RECORD,
                    source_id=record.ticket_id,
                    title=f"Synthetic ticket {record.ticket_id}",
                    payload=payload,
                )
            ],
        )
