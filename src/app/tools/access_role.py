"""Controlled synthetic IAM role-change capability."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.actions import ActionResultStatus, ControlledToolResult
from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceType
from app.domain.repositories import SyntheticRepository
from app.domain.tasks import ToolExecutionContext
from app.tools.evidence import evidence_reference


class ChangeAccessRoleArguments(StrictModel):
    """Validated identifiers and target role for a synthetic IAM change."""

    subject_id: str = Field(pattern=r"^USR-[0-9]{4}$")
    new_role: Literal["viewer", "support_agent", "billing_agent", "administrator"]


class ChangeAccessRoleResult(ControlledToolResult):
    """Resulting synthetic account state and version."""

    subject_id: str
    role: str
    version: int | None = None


class ChangeAccessRoleTool:
    """Change an isolated synthetic role without external IAM side effects."""

    name = "change_access_role"
    description = (
        "Change a user's role only in the isolated synthetic IAM table. This tool does not "
        "enforce business approval policy; the baseline agent must interpret retrieved policy "
        "and may request human review. No real identity system is modified."
    )
    input_model = ChangeAccessRoleArguments

    def __init__(self, repository: SyntheticRepository) -> None:
        self._repository = repository

    def execute(
        self,
        arguments: ChangeAccessRoleArguments,
        context: ToolExecutionContext,
    ) -> ChangeAccessRoleResult:
        """Apply an idempotent role change within the trusted case context."""
        record, changed = self._repository.change_access_role(
            context.case_id,
            arguments.subject_id,
            arguments.new_role,
        )
        if record is None:
            return ChangeAccessRoleResult(
                message="The synthetic account was not found; no role changed.",
                outcome_status=ActionResultStatus.NO_CHANGE,
                subject_id=arguments.subject_id,
                role="not_found",
            )
        payload = record.model_dump(mode="json")
        return ChangeAccessRoleResult(
            message=(
                "The role was changed in the synthetic IAM table."
                if changed
                else "The synthetic account already had the requested role."
            ),
            state_changed=changed,
            outcome_status=(
                ActionResultStatus.EXECUTED if changed else ActionResultStatus.NO_CHANGE
            ),
            subject_id=record.subject_id,
            role=record.role,
            version=record.version,
            evidence=[
                evidence_reference(
                    evidence_id=(f"access:{context.case_id}:{record.subject_id}:v{record.version}"),
                    evidence_type=EvidenceType.BUSINESS_RECORD,
                    source_id=record.subject_id,
                    title=f"Synthetic access account {record.subject_id}",
                    payload=payload,
                )
            ],
        )
