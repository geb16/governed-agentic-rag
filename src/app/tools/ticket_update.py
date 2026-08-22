"""Controlled status changes for case-partitioned synthetic tickets."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.actions import ActionResultStatus, ControlledToolResult
from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceType
from app.domain.repositories import SyntheticRepository
from app.domain.tasks import ToolExecutionContext
from app.tools.evidence import evidence_reference


class TicketUpdateArguments(StrictModel):
    """Validated ticket identifier and finite target status."""

    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")
    new_status: Literal["open", "in_progress", "resolved", "closed"]


class TicketUpdateResult(ControlledToolResult):
    """Resulting ticket status and optional updated version."""

    ticket_id: str
    status: str
    version: int | None = None


class TicketUpdateTool:
    """Change only synthetic ticket state inside the trusted case partition."""

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
        """Apply a status change and return integrity-addressed ticket evidence."""
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
