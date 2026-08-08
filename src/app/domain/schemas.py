"""Strict task, model-turn, evidence, action, and HTTP response contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base contract that strips strings and rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentStatus(StrEnum):
    """Terminal states returned by a baseline invocation."""

    COMPLETED = "completed"
    REFUSED = "refused"
    FAILED = "failed"


class ToolStatus(StrEnum):
    """Deterministic dispatch states recorded for a tool proposal."""

    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


class EvidenceType(StrEnum):
    """Origins supported by the governance-neutral evidence contract."""

    KNOWLEDGE_CHUNK = "knowledge_chunk"
    TOOL_RESULT = "tool_result"
    BUSINESS_RECORD = "business_record"


class ActionResultStatus(StrEnum):
    """Business outcome states independent of transport or model providers."""

    EXECUTED = "executed"
    NO_CHANGE = "no_change"
    DENIED = "denied"
    FAILED = "failed"


class EvidenceReference(StrictModel):
    """Stable metadata identifying evidence without embedding its full content."""

    evidence_id: str = Field(min_length=1, max_length=300)
    evidence_type: EvidenceType
    source_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class ControlledToolResult(StrictModel):
    """Common result envelope implemented by every allowlisted tool."""

    message: str = Field(min_length=1, max_length=500)
    state_changed: bool = False
    outcome_status: ActionResultStatus = ActionResultStatus.EXECUTED
    simulated: bool = True
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ToolExecutionContext(StrictModel):
    """
    Trusted invocation context injected by the application,
    not provided by the user / model.
    """

    case_id: str = Field(pattern=r"^case_[a-zA-Z0-9_-]+$")
    request_id: str
    requester_id: str


class Citation(StrictModel):
    """Caller-facing citation to an approved retrieved knowledge chunk."""

    chunk_id: str
    document_id: str
    title: str
    score: float = Field(ge=0.0, le=1.0)


class TaskRequest(StrictModel):
    """Governance-neutral request shared by both experimental conditions."""

    request_id: str = Field(
        default_factory=lambda: f"req_{uuid4().hex}",
        pattern=r"^req_[a-zA-Z0-9_-]+$",
    )
    case_id: str = Field(default="case_default", pattern=r"^case_[a-zA-Z0-9_-]+$")
    requester_id: str = Field(min_length=2, max_length=128)
    query: str = Field(min_length=5, max_length=4_000)

    @field_validator("query")
    @classmethod
    def require_meaningful_query(cls, value: str) -> str:
        """Reject queries that cannot express a minimally meaningful task.

        Args:
            value: Normalized query text.

        Returns:
            The validated query.

        Raises:
            ValueError: If the query contains fewer than two whitespace-delimited words.
        """
        if len(value.split()) < 2:
            raise ValueError("query must contain at least two words")
        return value


class BaselineRequest(TaskRequest):
    """Phase 3 API name for the shared task request contract."""


class ActionProposal(StrictModel):
    """A model-proposed tool action recorded before deterministic dispatch."""

    proposal_id: str
    action_type: str
    arguments: dict[str, Any]


class ActionOutcome(StrictModel):
    """Governance-neutral result from controlled simulated tool execution."""

    outcome_id: str
    status: ActionResultStatus
    case_id: str
    message: str = Field(min_length=1, max_length=500)
    state_changed: bool
    simulated: bool = True
    error_code: str | None = None
    retryable: bool = False


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


class AgentDraft(StrictModel):
    """Schema returned by the model and validated before it reaches callers."""

    answer: str = Field(min_length=1, max_length=6_000)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=12)
    grounded: bool


class ModelToolCall(StrictModel):
    """Provider-neutral representation of one proposed function call."""

    call_id: str
    name: str
    arguments_json: str


class ModelTurn(StrictModel):
    """Provider-neutral result of one model interaction."""

    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    final: AgentDraft | None = None
    continuation_items: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)


class RetrievedChunk(StrictModel):
    """Ranked and integrity-addressed unit of approved knowledge."""

    chunk_id: str
    document_id: str
    title: str
    content: str
    source_path: str
    score: float = Field(ge=0.0, le=1.0)
    content_sha256: str


class Usage(StrictModel):
    """Aggregate provider-reported token counts for one invocation."""

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


class HealthResponse(StrictModel):
    """Liveness or readiness status returned by health endpoints."""

    service: str
    version: str
    status: Literal["ok", "ready", "not_ready"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
