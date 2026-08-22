"""Governance-neutral contracts for proposed and controlled tool actions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceReference


class ActionResultStatus(StrEnum):
    """Business outcome states independent of transport or model providers."""

    EXECUTED = "executed"
    NO_CHANGE = "no_change"
    DENIED = "denied"
    FAILED = "failed"


class ControlledToolResult(StrictModel):
    """Common result envelope implemented by every allowlisted tool."""

    message: str = Field(min_length=1, max_length=500)
    state_changed: bool = False
    outcome_status: ActionResultStatus = ActionResultStatus.EXECUTED
    simulated: bool = True
    evidence: list[EvidenceReference] = Field(default_factory=list)


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
