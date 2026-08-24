"""Unit contracts for the constructor-compatible baseline façade."""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from app.baseline.agent import BaselineAgent
from app.baseline.application.contracts import AgentStatus, BaselineRequest
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.security import stable_safety_identifier
from app.domain.evidence import RetrievedChunk
from app.domain.model import AgentDraft, ModelToolCall, ModelTurn
from app.tools.response_drafter import ResponseDrafterTool


class FakeRepository:
    """Minimal case-reader double with configurable existence behavior."""

    def __init__(self, *, case_exists: bool = True) -> None:
        self._case_exists = case_exists

    def case_exists(self, case_id: str) -> bool:
        """Return the configured case-existence result."""
        return self._case_exists


class FakeRetriever:
    """Retrieval double returning a fixed ordered chunk list."""

    backend_name = "fake"

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """Return the configured chunks without ranking or truncation."""
        return self._chunks


class FakeModel:
    """Model-gateway double returning scripted turns in order."""

    model_name = "fake-model"

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = turns
        self.calls = 0
        self.safety_identifiers: list[str] = []

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        """Return the next scripted turn and count the invocation."""
        del input_items, instructions, tools
        self.calls += 1
        self.safety_identifiers.append(safety_identifier)
        return self._turns.pop(0)


def _request() -> BaselineRequest:
    return BaselineRequest(
        case_id="case_default",
        requester_id="requester-1",
        query="Explain the refund policy",
    )


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-refund",
        document_id="refund-policy",
        title="Refund policy",
        content="Refunds require an eligible ticket.",
        source_path="refund_policy.md",
        score=0.9,
        content_sha256="a" * 64,
    )


def _agent(
    *,
    model: FakeModel,
    repository: FakeRepository | None = None,
    settings: Settings | None = None,
    tool_router: ToolRouter | None = None,
) -> BaselineAgent:
    return BaselineAgent(
        settings=settings or Settings(),
        retriever=FakeRetriever([_chunk()]),
        model=model,
        tool_router=tool_router or ToolRouter([]),
        repository=repository or FakeRepository(),  # type: ignore [arg-type]
    )


def test_compatibility_facade_completes_grounded_response() -> None:
    """Preserve response metadata, usage, and citations through the façade."""
    model = FakeModel(
        [
            ModelTurn(
                final=AgentDraft(
                    answer="Eligible refunds require a ticket.",
                    cited_chunk_ids=["chunk-refund"],
                    grounded=True,
                ),
                input_tokens=12,
                output_tokens=7,
            )
        ]
    )

    response = _agent(model=model).invoke(_request())

    assert response.status == AgentStatus.COMPLETED
    assert response.retrieval_backend == "fake"
    assert response.model == "fake-model"
    assert response.usage.input_tokens == 12
    assert [citation.chunk_id for citation in response.citations] == ["chunk-refund"]


def test_facade_never_reuses_inbound_api_key_for_provider_identity() -> None:
    """Derive provider pseudonymization only from the dedicated safety secret."""
    settings = Settings(
        api_key=SecretStr("inbound-authentication-key"),
        safety_identifier_secret=SecretStr("dedicated-safety-key"),
    )
    model = FakeModel(
        [
            ModelTurn(
                final=AgentDraft(
                    answer="The request is not grounded in retrieved policy.",
                    grounded=False,
                )
            )
        ]
    )

    _agent(model=model, settings=settings).invoke(_request())

    assert model.safety_identifiers == [
        stable_safety_identifier("requester-1", "dedicated-safety-key")
    ]
    assert model.safety_identifiers != [
        stable_safety_identifier("requester-1", "inbound-authentication-key")
    ]


def test_missing_case_short_circuits_before_model_call() -> None:
    """Reject an unknown synthetic case before spending a model call."""
    model = FakeModel([])

    response = _agent(
        model=model,
        repository=FakeRepository(case_exists=False),
    ).invoke(_request())

    assert response.status == AgentStatus.FAILED
    assert response.error_code == "synthetic_case_not_found"
    assert model.calls == 0


def test_tool_turn_continues_to_a_final_response() -> None:
    """Carry controlled tool output and usage into a subsequent final turn."""
    model = FakeModel(
        [
            ModelTurn(
                tool_calls=[
                    ModelToolCall(
                        call_id="call-1",
                        name="response_drafter",
                        arguments_json=(
                            '{"audience":"customer","purpose":"Explain status",'
                            '"key_points":["The request is under review"]}'
                        ),
                    )
                ],
                continuation_items=[{"type": "function_call", "call_id": "call-1"}],
                input_tokens=5,
                output_tokens=3,
            ),
            ModelTurn(
                final=AgentDraft(
                    answer="A simulated response draft was created.",
                    grounded=False,
                ),
                input_tokens=8,
                output_tokens=4,
            ),
        ]
    )

    response = _agent(
        model=model,
        tool_router=ToolRouter([ResponseDrafterTool()]),
    ).invoke(_request())

    assert response.status == AgentStatus.COMPLETED
    assert response.usage.input_tokens == 13
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "response_drafter"
    assert response.evidence[0].evidence_id.startswith("draft:case_default:")


def test_tool_router_exposes_strict_provider_specs() -> None:
    """Expose only strict schemas for tools registered with the router."""
    router = ToolRouter([ResponseDrafterTool()])

    assert router.specs == [
        {
            "type": "function",
            "name": "response_drafter",
            "description": ResponseDrafterTool.description,
            "parameters": ResponseDrafterTool.input_model.model_json_schema(),
            "strict": True,
        }
    ]
