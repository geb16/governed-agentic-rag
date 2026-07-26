from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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