"""Reusable deterministic doubles and composition helpers for baseline tests."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.application.baseline.ports import ModelGateway
from app.baseline.agent import BaselineAgent
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.schemas import ModelTurn, ToolExecutionContext
from app.domain.support import DEFAULT_CASE_FIXTURE
from app.persistence.repository import SqliteSyntheticRepository
from app.rag.retriever import KnowledgeRetriever
from app.tools.faults import RepositoryFaultInjector
from app.tools.registry import build_shared_tools


class ScriptedModel(ModelGateway):
    """Deterministic model double for baseline orchestration tests."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns: Iterator[ModelTurn] = iter(turns)
        self.calls: list[dict[str, Any]] = []

    @property
    def model_name(self) -> str:
        """Return stable provider metadata for response assertions."""
        return "scripted-test-model"

    def complete(
        self,
        *,
        input_items: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        safety_identifier: str,
    ) -> ModelTurn:
        """Record gateway inputs and return the next scripted model turn."""
        self.calls.append(
            {
                "input_items": input_items.copy(),
                "instructions": instructions,
                "tools": tools,
                "safety_identifier": safety_identifier,
            }
        )
        return next(self._turns)


def tool_context(case_id: str = "case_default") -> ToolExecutionContext:
    """Build trusted invocation context for controlled-tool integration tests."""

    return ToolExecutionContext(
        case_id=case_id,
        request_id="req_freeze_test",
        requester_id="evaluation_user",
    )


def build_agent(
    settings: Settings,
    retriever: KnowledgeRetriever,
    model: ScriptedModel,
) -> BaselineAgent:
    """Compose the baseline with real local adapters and a scripted model."""

    repository = SqliteSyntheticRepository(settings.synthetic_database_path)
    repository.initialize()
    if not repository.case_exists(DEFAULT_CASE_FIXTURE.case_id):
        repository.create_case(DEFAULT_CASE_FIXTURE)
    router = ToolRouter(
        build_shared_tools(retriever, repository),
        fault_injector=RepositoryFaultInjector(repository),
    )
    return BaselineAgent(
        settings=settings,
        retriever=retriever,
        model=model,
        tool_router=router,
        repository=repository,
    )
