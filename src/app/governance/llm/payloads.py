"""Project application contracts into bounded provider payloads.

Payloads include only data required by the active stage. They omit credentials, raw
approval-principal identity, persistence details, audit hashes, and hidden reasoning.
All values are presented to the provider as untrusted JSON data.
"""

from __future__ import annotations

from typing import Any

from app.governance.contracts.state import WorkflowState
from app.governance.contracts.tasks import (
    ClassificationDraft,
    GovernedRequest,
    RetrievalResult,
)
from app.governance.contracts.tools import ToolDefinition


def classification_payload(request: GovernedRequest) -> dict[str, Any]:
    """Build the minimal request payload required for task classification.

    Args:
        request: Neutral governed request.

    Returns:
        A JSON-compatible mapping containing request, case, and query data.
    """
    return {
        "USER_REQUEST": {
            "request_id": request.request_id,
            "case_id": request.case_id,
            "query": request.query,
        }
    }


def proposal_payload(
    request: GovernedRequest,
    classification: ClassificationDraft,
    retrieval: RetrievalResult,
    tools: list[ToolDefinition],
) -> dict[str, Any]:
    """Build the evidence- and allowlist-bounded proposal payload.

    Args:
        request: Original governed request.
        classification: Validated task classification.
        retrieval: Retrieved knowledge chunks eligible for proposal grounding.
        tools: Allowlisted provider-neutral capability schemas.

    Returns:
        JSON-compatible stage-three context with no executable tool references.
    """
    return {
        "USER_REQUEST": {
            "request_id": request.request_id,
            "case_id": request.case_id,
            "query": request.query,
        },
        "CLASSIFICATION": classification.model_dump(mode="json"),
        "RETRIEVED_KNOWLEDGE": [
            {
                "chunk_id": chunk.chunk_id,
                "title": chunk.title,
                "content": chunk.content,
            }
            for chunk in retrieval.chunks
        ],
        "ALLOWLISTED_SIMULATED_TOOLS": [tool.model_dump(mode="json") for tool in tools],
    }


def final_payload(state: WorkflowState) -> dict[str, Any]:
    """Project persisted decisions and evidence identities for final drafting.

    Args:
        state: Current workflow aggregate.

    Returns:
        JSON-compatible terminal context excluding infrastructure and security secrets.
    """
    return {
        "WORKFLOW_STATUS": state.status.value,
        "CLASSIFICATION": _dump(state.classification),
        "PROPOSED_ACTION": _dump(state.proposal),
        "RISK_ASSESSMENT": _dump(state.risk),
        "APPROVAL_ROUTE": _dump(state.approval_route),
        "APPROVALS": [item.model_dump(mode="json") for item in state.approvals],
        "RECOVERY": _dump(state.recovery),
        "TOOL_OUTCOMES": [
            {
                "tool_name": call.tool_name,
                "status": call.status.value,
                "summary": call.result_summary,
                "evidence_ids": [item.evidence_id for item in call.evidence],
            }
            for call in state.tool_calls
        ],
        "AVAILABLE_EVIDENCE": [
            {
                "evidence_id": item.evidence_id,
                "title": item.title,
                "source_id": item.source_id,
            }
            for item in (state.retrieval.evidence if state.retrieval else [])
        ],
        "ERROR_CODE": state.error_code,
    }


def _dump(value: Any | None) -> dict[str, Any] | None:
    """Serialize an optional Pydantic contract using JSON-compatible values."""
    return value.model_dump(mode="json") if value is not None else None
