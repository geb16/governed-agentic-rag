"""Defines raw and normalized records retained for each invocation.

Raw observations preserve execution evidence and system-specific telemetry.
Normalized observations expose condition-comparable fields while retaining a
SHA-256 identity of their source record.

References:
    [1] NIST, "Secure Hash Standard (SHS)," FIPS 180-4.
        https://doi.org/10.6028/NIST.FIPS.180-4
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from paired_agent_evaluation.domain.executions import ExecutionKey, StrictModel


class AcceptanceStatus(StrEnum):
    """Indicates whether a provider request crossed the acceptance boundary."""

    ACCEPTED = "accepted"
    INVALID = "invalid"


class ObservedRoute(StrEnum):
    """Classifies the externally observable outcome of an execution."""

    ANSWER = "answer"
    EXECUTE = "execute"
    HUMAN_REVIEW = "human_review"
    CLARIFY = "clarify"
    DENY = "deny"
    SAFE_TERMINATE = "safe_terminate"


class RetrievedEvidence(StrictModel):
    """Records a retrieved chunk and its content identity."""

    chunk_id: str
    document_id: str
    title: str
    content: str
    content_sha256: str
    score: float = Field(ge=0, le=1)


class BusinessState(StrictModel):
    """Captures mutable business records associated with an evaluation case."""

    tickets: list[dict[str, Any]] = Field(default_factory=list)
    access_accounts: list[dict[str, Any]] = Field(default_factory=list)
    refunds: list[dict[str, Any]] = Field(default_factory=list)
    escalations: list[dict[str, Any]] = Field(default_factory=list)

    def business_projection(self) -> dict[str, Any]:
        """Returns state used to measure business effects, excluding escalations."""
        return {
            "tickets": self.tickets,
            "access_accounts": self.access_accounts,
            "refunds": self.refunds,
        }


class RawExecution(StrictModel):
    """Preserves inputs, outputs, telemetry, state, and errors for one execution."""

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
    audit_chain_valid: bool | None = None
    audit_workflow_id: str | None = None
    audit_trace_id: str | None = None
    audit_request_id: str | None = None
    operational_events: list[dict[str, Any]] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_acceptance_consistency(self) -> RawExecution:
        """Keeps the explicit acceptance flag aligned with its status enum."""
        if self.request_accepted != (self.acceptance == AcceptanceStatus.ACCEPTED):
            raise ValueError("request_accepted must match acceptance status")
        return self


class ToolAttempt(StrictModel):
    """Describes one normalized tool invocation and its observed effect."""

    tool_name: str
    arguments: dict[str, Any]
    status: str
    state_changed: bool
    error_code: str | None = None
    retryable: bool = False


class NormalizedObservation(StrictModel):
    """Stores condition-comparable facts derived from one raw execution."""

    schema_version: int = 1
    key: ExecutionKey
    acceptance: AcceptanceStatus
    observed_route: ObservedRoute | None = None
    route_source: str | None = None
    route_requires_adjudication: bool = False
    answer: str | None = None
    citations: list[str] = Field(default_factory=list)
    citation_membership_valid: bool = False
    retrieved_document_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_documents: dict[str, str] = Field(default_factory=dict)
    tool_attempts: list[ToolAttempt] = Field(default_factory=list)
    approval_roles: list[str] = Field(default_factory=list)
    approval_decisions: list[dict[str, Any]] = Field(default_factory=list)
    business_state_changed: bool = False
    any_state_changed: bool = False
    recovery_disposition: str | None = None
    recovery_attempts: int = 0
    terminal_error_code: str | None = None
    trace_facts: list[str] = Field(default_factory=list)
    audit_chain_valid: bool | None = None
    audit_correlation_valid: bool | None = None
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    raw_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
