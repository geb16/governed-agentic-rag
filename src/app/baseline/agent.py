"""Compatibility façade that wires legacy constructor inputs to the use case."""

from __future__ import annotations

from app.application.baseline.policy import AgentRuntimePolicy
from app.application.baseline.ports import ModelGateway
from app.application.baseline.service import BaselineAgentService
from app.baseline.guardrails import InputGuardrail, OutputGuardrail
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.domain.repositories import SyntheticRepository
from app.rag.retriever import Retriever


class BaselineAgent(BaselineAgentService):
    """Compatibility facade for the baseline invocation application service.

    Existing imports and constructor arguments remain stable while orchestration
    now lives in the application layer behind explicit ports.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        retriever: Retriever,
        model: ModelGateway,
        tool_router: ToolRouter,
        repository: SyntheticRepository,
        input_guardrail: InputGuardrail | None = None,
        output_guardrail: OutputGuardrail | None = None,
    ) -> None:
        resolved_input_guardrail = input_guardrail or InputGuardrail()
        resolved_output_guardrail = output_guardrail or OutputGuardrail()

        # Retain the original attributes for callers that inspect configured adapters.
        self.settings = settings
        self.retriever = retriever
        self.model = model
        self.tool_router = tool_router
        self.repository = repository
        self.input_guardrail = resolved_input_guardrail
        self.output_guardrail = resolved_output_guardrail

        super().__init__(
            policy=AgentRuntimePolicy(
                max_query_chars=settings.max_query_chars,
                max_agent_turns=settings.max_agent_turns,
                max_tool_calls=settings.max_tool_calls,
                safety_identifier_secret=(
                    settings.api_key.get_secret_value()
                    if settings.api_key is not None
                    else "phase3-development-only"
                ),
            ),
            retriever=retriever,
            model=model,
            tool_gateway=tool_router,
            case_reader=repository,
            input_guardrail=resolved_input_guardrail,
            output_guardrail=resolved_output_guardrail,
        )


__all__ = ["BaselineAgent"]
