from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.schemas import (
    AgentDraft,
    AgentStatus,
    BaselineRequest,
    ModelToolCall,
    ModelTurn,
    ToolStatus,
)
from app.domain.support import FailureMode, FaultPlan
from app.persistence.repository import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.response_drafter import ResponseDrafterTool
from tests.support.baseline import ScriptedModel, build_agent, tool_context


def test_fault_plan_fails_exact_number_of_attempts_then_allows_execution(
    repository: SqliteSyntheticRepository,
) -> None:
    repository.set_fault_plan(
        "case_default",
        FaultPlan(
            tool_name="response_drafter",
            mode=FailureMode.TRANSIENT_ERROR,
            failures=1,
            error_code="simulated_upstream_503",
        ),
    )
    router = ToolRouter(
        [ResponseDrafterTool()],
        fault_injector=RepositoryFaultInjector(repository),
    )
    arguments = (
        '{"audience":"customer","purpose":"Explain next steps",'
        '"key_points":["A human reviewer will respond."]}'
    )

    first = router.execute(
        call_id="call_fault_1",
        name="response_drafter",
        arguments_json=arguments,
        context=tool_context(),
    )
    second = router.execute(
        call_id="call_fault_2",
        name="response_drafter",
        arguments_json=arguments,
        context=tool_context(),
    )

    assert first.record.status == ToolStatus.FAILED
    assert first.record.outcome.error_code == "simulated_upstream_503"
    assert first.record.outcome.retryable is True
    assert second.record.status == ToolStatus.SUCCEEDED


def test_baseline_can_observe_retryable_failure_and_choose_one_retry(
    settings: Settings,
    retriever: KnowledgeRetriever,
    repository: SqliteSyntheticRepository,
) -> None:
    repository.set_fault_plan(
        "case_default",
        FaultPlan(
            tool_name="response_drafter",
            mode=FailureMode.TIMEOUT,
            failures=1,
            error_code="simulated_timeout",
        ),
    )
    arguments = (
        '{"audience":"customer","purpose":"Explain next steps",'
        '"key_points":["A reviewer will respond."]}'
    )
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        call_id="call_retry_1",
                        name="response_drafter",
                        arguments_json=arguments,
                    )
                ],
                continuation_items=[
                    {
                        "type": "function_call",
                        "call_id": "call_retry_1",
                        "name": "response_drafter",
                        "arguments": arguments,
                    }
                ],
            ),
            ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        call_id="call_retry_2",
                        name="response_drafter",
                        arguments_json=arguments,
                    )
                ],
                continuation_items=[
                    {
                        "type": "function_call",
                        "call_id": "call_retry_2",
                        "name": "response_drafter",
                        "arguments": arguments,
                    }
                ],
            ),
            ModelTurn(
                final=AgentDraft(
                    answer="A simulated response draft was created after one retry.",
                    cited_chunk_ids=[],
                    grounded=False,
                )
            ),
        ]
    )
    agent = build_agent(settings, retriever, model)

    response = agent.invoke(
        BaselineRequest(
            requester_id="support_user",
            query="Draft an update for ticket TKT-1001.",
        )
    )

    assert response.status == AgentStatus.COMPLETED
    assert [record.status for record in response.tool_calls] == [
        ToolStatus.FAILED,
        ToolStatus.SUCCEEDED,
    ]
    assert response.tool_calls[0].outcome.retryable is True
