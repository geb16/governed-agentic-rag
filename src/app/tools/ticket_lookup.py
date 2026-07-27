from __future__ import annotations

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


class TicketLookupArguments(StrictModel):
    ticket_id: str = Field(pattern=r"^TKT-[0-9]{4}$")


class TicketLookupResult(ControlledToolResult):
    ticket_id: str
    status: str
    category: str
    summary: str
    version: int


class TicketLookupTool:
    name = "ticket_lookup"
    description = (
        "Read a ticket from the current isolated synthetic evaluation case. "
        "This tool cannot create or modify tickets."
    )
    input_model = TicketLookupArguments

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def execute(
        self,
        arguments: TicketLookupArguments,
        context: ToolExecutionContext,
    ) -> TicketLookupResult:
        record = self._repository.get_ticket(context.case_id, arguments.ticket_id)
        if record is None:
            return TicketLookupResult(
                message="No synthetic ticket exists with this identifier in the current case.",
                outcome_status=ActionResultStatus.NO_CHANGE,
                ticket_id=arguments.ticket_id,
                status="not_found",
                category="unknown",
                summary="No synthetic ticket exists with this identifier.",
                version=1,
            )
        payload = record.model_dump(mode="json")
        return TicketLookupResult(
            message="Retrieved the synthetic ticket.",
            **payload,
            evidence=[
                evidence_reference(
                    evidence_id=(
                        f"ticket:{context.case_id}:{record.ticket_id}:v{record.version}"
                    ),
                    evidence_type=EvidenceType.BUSINESS_RECORD,
                    source_id=record.ticket_id,
                    title=f"Synthetic ticket {record.ticket_id}",
                    payload=payload,
                )
            ],
        )
