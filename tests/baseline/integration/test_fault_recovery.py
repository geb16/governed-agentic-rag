from app.baseline.tool_router import ToolRouter
from app.domain.schemas import ToolStatus
from app.domain.support import FailureMode, FaultPlan
from app.persistence.repository import SqliteSyntheticRepository
from app.tools.faults import RepositoryFaultInjector
from app.tools.response_drafter import ResponseDrafterTool
from tests.support.baseline import tool_context


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

