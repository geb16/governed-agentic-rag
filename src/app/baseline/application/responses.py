"""Build consistent public responses across every baseline exit path.

Single owner of the BaselineResponse contract: stamps adapter metadata
(retrieval backend, model name) and a UTC timestamp so completed, refused,
and failed paths stay uniform.
Core:
    - BaselineResponseFactory: creates fully populated BaselineResponse objects.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.baseline.application.contracts import (
    AgentStatus,
    BaselineRequest,
    BaselineResponse,
    SafetyResult,
    ToolCallRecord,
    Usage,
)
from app.domain.evidence import Citation, EvidenceReference


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
        """Create a timestamped response with stable adapter metadata.

        Args:
            request: Original task identity and case context.
            trace_id: Per-invocation operational trace identifier.
            status: Terminal application status.
            answer: Caller-facing result text.
            safety: Deterministic safety decision attached to the result.
            citations: Validated knowledge citations, if any.
            evidence: Knowledge and tool evidence, if any.
            tool_calls: Controlled tool execution records, if any.
            usage: Aggregate model token usage.
            error_code: Stable machine-readable failure code, if applicable.

        Returns:
            A fully populated baseline response contract.
        """
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
