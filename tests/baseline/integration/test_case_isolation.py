"""Persistence and tool-dispatch isolation across synthetic evaluation cases."""

from app.baseline.application.contracts import ToolStatus
from app.baseline.tool_router import ToolRouter
from app.domain.actions import ActionResultStatus
from app.domain.support import (
    DEFAULT_CASE_FIXTURE,
    AccessAccountRecord,
    SyntheticCaseFixture,
    TicketRecord,
)
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.tools.ticket_update import TicketUpdateTool
from tests.baseline.support import tool_context


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


def test_replacing_case_clears_actions_without_touching_other_cases(
    repository: SqliteSyntheticRepository,
) -> None:
    """Re-seed a case that has actions while leaving other case partitions intact."""
    other = DEFAULT_CASE_FIXTURE.model_copy(update={"case_id": "case_other"})
    repository.create_case(other)
    for case_id in ("case_default", "case_other"):
        repository.issue_refund(case_id, "TKT-1001", 500, "USD", "refund-1")
        repository.request_human_review(case_id, "TKT-1001", "check", "supervisor", "review-1")
    repository.update_ticket_status("case_default", "TKT-1001", "closed")

    repository.create_case(DEFAULT_CASE_FIXTURE, replace=True)

    ticket = repository.get_ticket("case_default", "TKT-1001")
    assert ticket is not None and ticket.status == "open"
    assert repository.issue_refund("case_default", "TKT-1001", 500, "USD", "refund-1")[1]
    assert not repository.issue_refund("case_other", "TKT-1001", 500, "USD", "refund-1")[1]
