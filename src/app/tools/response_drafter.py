"""Controlled plain-text drafting with no delivery side effect."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.actions import ControlledToolResult
from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceType
from app.domain.tasks import ToolExecutionContext
from app.tools.evidence import evidence_reference


class ResponseDrafterArguments(StrictModel):
    """Validated audience, purpose, and bounded response points."""

    audience: Literal["customer", "support_staff", "policy_owner"]
    purpose: str = Field(min_length=3, max_length=200)
    key_points: list[str] = Field(min_length=1, max_length=8)


class ResponseDrafterResult(ControlledToolResult):
    """Plain-text draft explicitly marked as undelivered."""

    draft: str
    delivered: bool = False


class ResponseDrafterTool:
    """Create a normalized simulated response draft without sending it."""

    name = "response_drafter"
    description = (
        "Create a simulated plain-text response draft. It never sends a message "
        "or writes to an external system."
    )
    input_model = ResponseDrafterArguments

    def execute(
        self,
        arguments: ResponseDrafterArguments,
        context: ToolExecutionContext,
    ) -> ResponseDrafterResult:
        """Normalize key points and return an integrity-addressed draft."""
        safe_points = [
            point.replace("\r", " ").replace("\n", " ").strip()[:300]
            for point in arguments.key_points
        ]
        draft = f"Audience: {arguments.audience}\nPurpose: {arguments.purpose}\n" + "\n".join(
            f"- {point}" for point in safe_points
        )
        payload = {"audience": arguments.audience, "purpose": arguments.purpose, "draft": draft}
        return ResponseDrafterResult(
            message="Created a simulated response draft; no message was delivered.",
            draft=draft,
            evidence=[
                evidence_reference(
                    evidence_id=f"draft:{context.case_id}:{context.request_id}",
                    evidence_type=EvidenceType.TOOL_RESULT,
                    source_id=context.request_id,
                    title="Simulated response draft",
                    payload=payload,
                )
            ],
        )
