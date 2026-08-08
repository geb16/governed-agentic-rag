"""Behavioral boundaries distinguishing the baseline from Phase 4 governance."""

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
    """Allow the baseline model to request review without a formal risk router."""
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


# Testing the baseline LLM fails gracefully when a case_id is unknown.
# validate this happends before any model or tool execution occurs.
def test_unknown_case_fails_before_model_or_tool_execution(
    settings: Settings,
    retriever: KnowledgeRetriever,
) -> None:
    """Reject an unknown case before model reasoning or tool execution."""
    model = ScriptedModel([])
    agent = build_agent(settings, retriever, model)

    response = agent.invoke(
        BaselineRequest(
            case_id="case_missing",
            requester_id="support_user",
            query="Look up ticket TKT-1001 in this case.",
        )
    )

    assert response.status == AgentStatus.FAILED
    assert response.error_code == "synthetic_case_not_found"
    assert model.calls == []
