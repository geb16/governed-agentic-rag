from app.domain.schemas import (
    AgentDraft,
    AgentStatus,
    BaselineRequest,
    ModelTurn,
)
from app.rag.retriever import KnowledgeRetriever
from tests.support.baseline import ScriptedModel, build_agent


def test_agent_invocation_returns_valid_grounded_output(
    settings,
    retriever: KnowledgeRetriever,
) -> None:
    chunk = retriever.retrieve("refund 750 finance manager approval")[0]
    model = ScriptedModel(
        [
            ModelTurn(
                final=AgentDraft(
                    answer="A refund of 750 requires finance manager approval.",
                    cited_chunk_ids=[chunk.chunk_id],
                    grounded=True,
                ),
                input_tokens=120,
                output_tokens=35,
            )
        ]
    )
    agent = build_agent(settings, retriever, model)

    response = agent.invoke(
        BaselineRequest(
            requester_id="pilot_user",
            query="What is required for a refund of 750?",
        )
    )

    assert response.status == AgentStatus.COMPLETED
    assert response.citations[0].chunk_id == chunk.chunk_id
    assert response.usage.input_tokens == 120
    assert response.model == "scripted-test-model"
    assert "System instructions outrank" in model.calls[0]["instructions"]
