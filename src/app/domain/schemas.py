from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentStatus(StrEnum):
    COMPLETED = "completed"
    REFUSED = "refused"
    FAILED = "failed"


class ToolStatus(StrEnum):
    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


class EvidenceType(StrEnum):
    KNOWLEDGE_CHUNK = "knowledge_chunk"
    TOOL_RESULT = "tool_result"
    BUSINESS_RECORD = "business_record"


class ActionResultStatus(StrEnum):
    EXECUTED = "executed"
    NO_CHANGE = "no_change"
    DENIED = "denied"
    FAILED = "failed"


class EvidenceReference(StrictModel):
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
    chunk_id: str
    document_id: str
    title: str
    score: float = Field(ge=0.0, le=1.0)


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
    call_id: str
    name: str
    arguments_json: str


class ModelTurn(StrictModel):
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    final: AgentDraft | None = None
    continuation_items: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

class RetrievedChunk(StrictModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    source_path: str
    score: float = Field(ge=0.0, le=1.0)
    content_sha256: str
