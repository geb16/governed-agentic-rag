from __future__ import annotations

from enum import StrEnum

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
