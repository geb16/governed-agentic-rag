"""Define application request, response, status, and tool-record contracts.

Strict Pydantic models and StrEnums shared by the service, tool router, and
HTTP layer; BaselineRequest reuses the domain TaskRequest unchanged.
Core:
    - AgentStatus, ToolStatus: terminal invocation and tool dispatch states.
    - BaselineRequest, BaselineResponse: public invocation contract.
    - ToolCallRecord: proposal, outcome, timing, and evidence of one tool call.
    - Usage, SafetyResult: token counts and the deterministic safety verdict.
References:
    [1] Pydantic, "Models." https://docs.pydantic.dev/latest/concepts/models/
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.domain.actions import ActionOutcome, ActionProposal
from app.domain.contracts import StrictModel
from app.domain.evidence import Citation, EvidenceReference
from app.domain.tasks import TaskRequest


class AgentStatus(StrEnum):
    """Terminal states returned by a baseline invocation."""

    COMPLETED = "completed"
    REFUSED = "refused"
    FAILED = "failed"


class ToolStatus(StrEnum):
    """Deterministic dispatch states recorded for a baseline tool proposal."""

    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


class BaselineRequest(TaskRequest):
    """Phase 3 API name for the shared task request contract."""


class ToolCallRecord(StrictModel):
    """Complete proposal, dispatch, outcome, timing, and evidence record."""

    call_id: str
    tool_name: str
    status: ToolStatus
    arguments: dict[str, Any]
    result_summary: str = Field(max_length=500)
    duration_ms: float = Field(ge=0.0)
    proposal: ActionProposal
    outcome: ActionOutcome
    evidence: list[EvidenceReference] = Field(default_factory=list)


class Usage(StrictModel):
    """Aggregate provider-reported token counts for one baseline invocation."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class SafetyResult(StrictModel):
    """Public deterministic safety decision and optional rule category."""

    blocked: bool
    category: str | None = None


class BaselineResponse(StrictModel):
    """Phase 3 terminal response for the shared task contract."""

    request_id: str
    case_id: str
    trace_id: str
    status: AgentStatus
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    retrieval_backend: str
    model: str
    usage: Usage = Field(default_factory=Usage)
    safety: SafetyResult
    error_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
