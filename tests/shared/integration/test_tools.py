"""Strict schemas, validation, simulation, and shared tool-registry contracts."""

from app.baseline.application.contracts import ToolStatus
from app.baseline.tool_router import ToolRouter
from app.domain.tasks import ToolExecutionContext
from app.infrastructure.persistence.sqlite import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.registry import build_shared_tools
from app.tools.response_drafter import ResponseDrafterTool
from app.tools.ticket_lookup import TicketLookupTool

CONTEXT = ToolExecutionContext(
    case_id="case_default",
    request_id="req_test",
    requester_id="test_user",
)


def test_tool_specs_are_strict_and_forbid_extra_properties(
    repository: SqliteSyntheticRepository,
) -> None:
    """Expose strict schemas that reject undeclared model arguments."""
    specs = ToolRouter([TicketLookupTool(repository), ResponseDrafterTool()]).specs

    assert all(spec["strict"] is True for spec in specs)
    assert all(spec["parameters"]["additionalProperties"] is False for spec in specs)


def test_tool_arguments_are_validated_before_execution(
    repository: SqliteSyntheticRepository,
) -> None:
    """Deny malformed and extra tool arguments before controlled execution."""
    router = ToolRouter([TicketLookupTool(repository)])

    result = router.execute(
        call_id="call_1",
        name="ticket_lookup",
        arguments_json='{"ticket_id":"../../secrets","extra":true}',
        context=CONTEXT,
    )

    assert result.record.status == ToolStatus.DENIED
    assert result.output_json == '{"error":"tool_arguments_invalid","retryable":false}'


def test_response_drafter_is_simulated_and_never_delivers() -> None:
    """Keep response drafting explicitly simulated and undelivered."""
    router = ToolRouter([ResponseDrafterTool()])

    result = router.execute(
        call_id="call_2",
        name="response_drafter",
        arguments_json=(
            '{"audience":"customer","purpose":"Explain next steps",'
            '"key_points":["Identity verification is required."]}'
        ),
        context=CONTEXT,
    )

    assert result.record.status == ToolStatus.SUCCEEDED
    assert '"simulated":true' in result.output_json
    assert '"delivered":false' in result.output_json


def test_shared_tool_registry_is_the_frozen_capability_set(
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    """Keep the ordered capability set identical across experimental conditions."""
    names = [tool.name for tool in build_shared_tools(retriever, repository)]

    assert names == [
        "policy_lookup",
        "ticket_lookup",
        "response_drafter",
        "update_ticket_status",
        "issue_refund",
        "change_access_role",
        "request_human_review",
    ]
