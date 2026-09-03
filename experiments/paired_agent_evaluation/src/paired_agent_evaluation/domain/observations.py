"""Raw and normalized observation contracts retained for every invocation."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from paired_agent_evaluation.domain.executions import ExecutionKey, StrictModel


class AcceptanceStatus(StrEnum):
    ACCEPTED = "accepted"
    INVALID = "invalid"


class ObservedRoute(StrEnum):
    ANSWER = "answer"
    EXECUTE = "execute"
    HUMAN_REVIEW = "human_review"
    CLARIFY = "clarify"
    DENY = "deny"
    SAFE_TERMINATE = "safe_terminate"


class RetrievedEvidence(StrictModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    content_sha256: str
    score: float = Field(ge=0, le=1)


class BusinessState(StrictModel):
    tickets: list[dict[str, Any]] = Field(default_factory=list)
    access_accounts: list[dict[str, Any]] = Field(default_factory=list)
    refunds: list[dict[str, Any]] = Field(default_factory=list)
    escalations: list[dict[str, Any]] = Field(default_factory=list)

    def business_projection(self) -> dict[str, Any]:
        return {
            "tickets": self.tickets,
            "access_accounts": self.access_accounts,
            "refunds": self.refunds,
        }


class RawExecution(StrictModel):
    schema_version: int = 1
    key: ExecutionKey
    acceptance: AcceptanceStatus
    request_accepted: bool
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime
    latency_ms: float = Field(ge=0)
    request: dict[str, Any]
    response: dict[str, Any] | None = None
    initial_response: dict[str, Any] | None = None
    retrieved: list[RetrievedEvidence] = Field(default_factory=list)
    retrieval_call_count: int = Field(default=0, ge=0)
    state_before: BusinessState
    state_after: BusinessState
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    operational_events: list[dict[str, Any]] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None


class ToolAttempt(StrictModel):
    tool_name: str
    arguments: dict[str, Any]
    status: str
    state_changed: bool
    error_code: str | None = None
    retryable: bool = False
