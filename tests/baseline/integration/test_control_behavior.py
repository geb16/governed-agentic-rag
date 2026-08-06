from app.core.config import Settings
from app.domain.schemas import (
    AgentDraft,
    AgentStatus,
    BaselineRequest,
    EvidenceType,
    ModelToolCall,
    ModelTurn,
)
from app.rag.retriever import KnowledgeRetriever
from tests.support.baseline import ScriptedModel, build_agent


# Test that the baseline LLM can choose to escalate a ticket to a human reviewer
def test_baseline_llm_can_choose_human_escalation_without_formal_router(
    settings: Settings,
    retriever: KnowledgeRetriever,
) -> None:
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        call_id="call_review",
                        name="request_human_review",
                        arguments_json=(
                            '{"ticket_id":"TKT-1001",'
                            '"reason":"Retrieved IAM policy requires manager review.",'
                            '"requested_role":"iam_manager",'
                            '"idempotency_key":"baseline_review_001"}'
                        ),
                    )
                ],
                continuation_items=[
                    {
                        "type": "function_call",
                        "call_id": "call_review",
                        "name": "request_human_review",
                        "arguments": "{}",
                    }
                ],
            ),
            ModelTurn(
                final=AgentDraft(
                    answer="The request was escalated for IAM manager review.",
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
            query="Escalate ticket TKT-1001 for the required IAM review.",
        )
    )

    assert response.status == AgentStatus.COMPLETED
    assert response.tool_calls[0].tool_name == "request_human_review"
    assert response.tool_calls[0].outcome.state_changed is True
    assert response.evidence[0].evidence_type == EvidenceType.BUSINESS_RECORD
    assert "formal risk classifier" in model.calls[0]["instructions"]