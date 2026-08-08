from __future__ import annotations

from datetime import UTC, datetime

from app.domain.schemas import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    Citation,
    EvidenceReference,
    SafetyResult,
    ToolCallRecord,
    Usage,
)


class BaselineResponseFactory:
    """Single owner for the public response contract and provider metadata."""

    def __init__(self, *, retrieval_backend: str, model_name: str) -> None:
        self._retrieval_backend = retrieval_backend
        self._model_name = model_name

    def create(
        self,
        *,
        request: BaselineRequest,
        trace_id: str,
        status: AgentStatus,
        answer: str,
        safety: SafetyResult,
        citations: list[Citation] | None = None,
        evidence: list[EvidenceReference] | None = None,
        tool_calls: list[ToolCallRecord] | None = None,
        usage: Usage | None = None,
        error_code: str | None = None,
    ) -> BaselineResponse:
        return BaselineResponse(
            request_id=request.request_id,
            case_id=request.case_id,
            trace_id=trace_id,
            status=status,
            answer=answer,
            citations=citations or [],
            evidence=evidence or [],
            tool_calls=tool_calls or [],
            retrieval_backend=self._retrieval_backend,
            model=self._model_name,
            usage=usage or Usage(),
            safety=safety,
            error_code=error_code,
            created_at=datetime.now(UTC),
        )
