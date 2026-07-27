from __future__ import annotations

import logging

from app.rag.retriever import Retriever

from app.baseline.guardrails import InputGuardrail, OutputGuardrail
from app.baseline.model import AgentModel
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.persistence.repository import SyntheticRepository

logger = logging.getLogger(__name__)


# BaselineAgent  orchestrates the RAG process, including retrieval, model interaction, 
# tool execution, and guardrail enforcement.
class BaselineAgent:

    def __init__(
        self,
        *,
        settings: Settings,
        retriever: Retriever,
        model: AgentModel,
        tool_router: ToolRouter,
        repository: SyntheticRepository,
        input_guardrail: InputGuardrail | None = None,
        output_guardrail: OutputGuardrail | None = None,
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.model = model
        self.tool_router = tool_router
        self.repository = repository
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.output_guardrail = output_guardrail or OutputGuardrail()