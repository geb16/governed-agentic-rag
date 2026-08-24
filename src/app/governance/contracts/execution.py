"""Define execution-recovery and final-answer validation contracts."""

from pydantic import Field

from app.domain.contracts import StrictModel
from app.governance.contracts.enums import RecoveryDisposition


class RecoveryResult(StrictModel):
    """Summarize bounded tool execution and its recovery outcome.

    ``attempts`` records actual dispatch attempts. ``retryable_exhausted``
    distinguishes a consumed retry budget from an immediate safe termination.
    """

    disposition: RecoveryDisposition
    attempts: int = Field(default=0, ge=0, le=5)
    error_code: str | None = None
    retryable_exhausted: bool = False


class GovernedFinalDraft(StrictModel):
    """Represent the model draft accepted only after groundedness validation.

    Cited identifiers must refer to evidence retrieved for the active workflow.
    The final stage fails closed when the draft is ungrounded or cites unknown
    evidence.
    """

    answer: str = Field(min_length=1, max_length=8_000)
    cited_evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    grounded: bool
