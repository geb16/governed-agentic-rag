"""Implement stage six: bounded tool execution and deterministic recovery.

Only catalog-validated arguments can reach the shared simulated router. Retryability
comes from structured tool outcomes, and the configured attempt bound prevents
unbounded loops or repeated side effects.
"""

from __future__ import annotations

import json
from uuid import uuid4

from app.baseline.application.contracts import ToolCallRecord, ToolStatus
from app.baseline.tool_router import ToolRouter
from app.domain.tasks import ToolExecutionContext
from app.governance.contracts import (
    ProposedAction,
    ProposedActionKind,
    RecoveryDisposition,
    RecoveryResult,
)


class RetryRecoveryStage:
    """Apply bounded deterministic retries to the shared simulated tool router.

    Args:
        tool_router: Shared allowlisted and schema-validating simulated router.
        max_attempts: Total dispatch attempts, constrained to one through five.

    Raises:
        ValueError: If ``max_attempts`` falls outside the supported safety bound.
    """

    def __init__(self, tool_router: ToolRouter, *, max_attempts: int = 3) -> None:
        """Initialize bounded recovery after validating the total attempt limit."""
        if not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        self._tool_router = tool_router
        self.max_attempts = max_attempts

    def run(
        self,
        proposal: ProposedAction,
        context: ToolExecutionContext,
    ) -> tuple[RecoveryResult, list[ToolCallRecord]]:
        """Execute a validated proposal or return a safe non-execution result.

        Args:
            proposal: Catalog-validated response or tool proposal.
            context: Trusted execution context containing synthetic case identity.

        Returns:
            Recovery disposition and ordered records for every attempted tool call.
            Response-only proposals return ``not_required`` with no calls.
        """
        if proposal.kind == ProposedActionKind.RESPOND:
            return (
                RecoveryResult(disposition=RecoveryDisposition.NOT_REQUIRED),
                [],
            )
        if proposal.validation_error or not proposal.tool_name:
            return (
                RecoveryResult(
                    disposition=RecoveryDisposition.SAFE_TERMINATION,
                    error_code=proposal.validation_error or "tool_name_missing",
                ),
                [],
            )

        records = []
        arguments_json = json.dumps(
            proposal.validated_arguments,
            sort_keys=True,
            separators=(",", ":"),
        )
        for attempt in range(1, self.max_attempts + 1):
            execution = self._tool_router.execute(
                call_id=f"call_{uuid4().hex}",
                name=proposal.tool_name,
                arguments_json=arguments_json,
                context=context,
            )
            records.append(execution.record)
            if execution.record.status == ToolStatus.SUCCEEDED:
                disposition = (
                    RecoveryDisposition.SUCCEEDED
                    if attempt == 1
                    else RecoveryDisposition.RETRIED_AND_SUCCEEDED
                )
                return RecoveryResult(disposition=disposition, attempts=attempt), records
            if not execution.record.outcome.retryable:
                return (
                    RecoveryResult(
                        disposition=RecoveryDisposition.SAFE_TERMINATION,
                        attempts=attempt,
                        error_code=execution.record.outcome.error_code,
                    ),
                    records,
                )
        return (
            RecoveryResult(
                disposition=RecoveryDisposition.SAFE_TERMINATION,
                attempts=self.max_attempts,
                error_code=records[-1].outcome.error_code,
                retryable_exhausted=True,
            ),
            records,
        )
