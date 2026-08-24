"""Implement stage one: bounded task and sensitivity classification.

Deterministic input-security findings bypass the model and produce a critical,
unsupported classification. Other requests use the provider-neutral model port and
carry only token usage and validated structured output into orchestration.
"""

from __future__ import annotations

from app.governance.contracts import (
    ClassificationResult,
    GovernedRequest,
    Sensitivity,
    TaskIntent,
    TaskType,
)
from app.governance.llm import GovernanceModel, ModelResult


class TaskClassificationStage:
    """Classify requests while giving deterministic security controls precedence.

    Args:
        model: Structured governance model port used for non-blocked requests.
    """

    def __init__(self, model: GovernanceModel) -> None:
        """Initialize classification with the structured model port."""
        self._model = model

    def run(
        self,
        request: GovernedRequest,
        *,
        safety_identifier: str,
        security_category: str | None = None,
    ) -> ModelResult[ClassificationResult]:
        """Produce a validated classification for one governed request.

        Args:
            request: Neutral task request shared with the baseline condition.
            safety_identifier: Pseudonymous provider safety identity.
            security_category: Deterministic input-guardrail finding, when present.

        Returns:
            Classification and provider usage; deterministic blocks report no usage.
        """
        if security_category is not None:
            return ModelResult(
                output=ClassificationResult(
                    intent=TaskIntent.SECURITY_ATTACK,
                    task_type=TaskType.UNSUPPORTED,
                    sensitivity=Sensitivity.CRITICAL,
                    confidence=1.0,
                    summary="Deterministic input control identified a security violation.",
                    security_category=security_category,
                )
            )
        result = self._model.classify(
            request,
            safety_identifier=safety_identifier,
        )
        return ModelResult(
            output=ClassificationResult(
                **result.output.model_dump(),
                security_category=None,
            ),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
