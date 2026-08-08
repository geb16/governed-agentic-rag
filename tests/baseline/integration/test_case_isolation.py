"""Persistence and tool-dispatch isolation across synthetic evaluation cases."""

from app.baseline.tool_router import ToolRouter
from app.domain.schemas import ActionResultStatus, ToolStatus
from app.domain.support import AccessAccountRecord, SyntheticCaseFixture, TicketRecord
from app.persistence.repository import SqliteSyntheticRepository
from app.tools.ticket_update import TicketUpdateTool
from tests.support.baseline import tool_context


def test_case_state_is_isolated_by_case_id(repository: SqliteSyntheticRepository) -> None:
    """Confine a synthetic write to the trusted case identifier in its context."""
    repository.create_case(
        SyntheticCaseFixture(
            case_id="case_isolated",
            tickets=[
                TicketRecord(
                    ticket_id="TKT-1001",
                    status="open",
                    category="identity_access",
                    summary="Independent copy for isolation testing.",
                    version=1,
                )
            ],
            access_accounts=[AccessAccountRecord(subject_id="USR-1001", role="viewer", version=1)],
        )
    )
    router = ToolRouter([TicketUpdateTool(repository)])
    result = router.execute(
        call_id="call_update",
        name="update_ticket_status",
        arguments_json='{"ticket_id":"TKT-1001","new_status":"closed"}',
        context=tool_context("case_isolated"),
    )

    assert result.record.status == ToolStatus.SUCCEEDED
    assert result.record.outcome.status == ActionResultStatus.EXECUTED
    isolated = repository.get_ticket("case_isolated", "TKT-1001")
    default = repository.get_ticket("case_default", "TKT-1001")
    assert isolated is not None and isolated.status == "closed"
    assert default is not None and default.status == "open"
