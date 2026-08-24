"""Define request, classification, retrieval, and proposal-stage contracts.

Draft models represent untrusted model output. Validated models add deterministic
security or allowlist results before data can cross into risk assessment and
execution.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from app.domain.contracts import StrictModel
from app.domain.evidence import EvidenceReference, RetrievedChunk
from app.domain.tasks import TaskRequest
from app.governance.contracts.enums import (
    ProposedActionKind,
    Sensitivity,
    TaskIntent,
    TaskType,
)


class GovernedRequest(TaskRequest):
    """Accept governed input identical to the neutral baseline request.

    Keeping the treatment input neutral preserves experimental comparability;
    governance metadata is produced by the workflow rather than supplied by users.
    """


class ClassificationDraft(StrictModel):
    """Represent bounded structured classification returned by the model."""

    intent: TaskIntent
    task_type: TaskType
    sensitivity: Sensitivity
    confidence: float = Field(ge=0.0, le=1.0)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    summary: str = Field(min_length=1, max_length=500)


class ClassificationResult(ClassificationDraft):
    """Add deterministic security classification to the model-generated draft."""

    security_category: str | None = None


class RetrievalResult(StrictModel):
    """Capture the selected retrieval route, source chunks, and evidence identities."""

    route: str
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class ProposedActionDraft(StrictModel):
    """Represent an untrusted model proposal before allowlist validation.

    Tool arguments remain JSON text so model output cannot be mistaken for trusted
    application data before strict schema validation.
    """

    kind: ProposedActionKind
    tool_name: str | None = Field(default=None, max_length=100)
    arguments_json: str = Field(default="{}", max_length=4_000)
    response_text: str | None = Field(default=None, max_length=6_000)
    confidence: float = Field(ge=0.0, le=1.0)
    missing_information: list[str] = Field(default_factory=list, max_length=12)
    rationale: str = Field(min_length=1, max_length=500)


class ProposedAction(ProposedActionDraft):
    """Carry a proposal enriched with deterministic tool-validation results.

    ``validated_arguments`` is the only argument mapping eligible for simulated
    dispatch. ``validation_error`` retains a bounded reason when validation fails.
    """

    proposal_id: str = Field(default_factory=lambda: f"proposal_{uuid4().hex}")
    validated_arguments: dict[str, Any] = Field(default_factory=dict)
    validation_error: str | None = None
