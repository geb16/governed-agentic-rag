"""Governance-neutral task request and trusted execution-context contracts."""

from __future__ import annotations

from uuid import uuid4

from pydantic import Field, field_validator

from app.domain.contracts import StrictModel


class ToolExecutionContext(StrictModel):
    """Trusted task identity injected by the application, never by the model."""

    case_id: str = Field(pattern=r"^case_[a-zA-Z0-9_-]+$")
    request_id: str
    requester_id: str


class TaskRequest(StrictModel):
    """Governance-neutral request shared by both experimental conditions."""

    request_id: str = Field(
        default_factory=lambda: f"req_{uuid4().hex}",
        pattern=r"^req_[a-zA-Z0-9_-]+$",
    )
    case_id: str = Field(default="case_default", pattern=r"^case_[a-zA-Z0-9_-]+$")
    requester_id: str = Field(min_length=2, max_length=128)
    query: str = Field(min_length=5, max_length=4_000)

    @field_validator("query")
    @classmethod
    def require_meaningful_query(cls, value: str) -> str:
        """Reject queries that cannot express a minimally meaningful task.

        Args:
            value: Normalized query text.

        Returns:
            The validated query.

        Raises:
            ValueError: If the query contains fewer than two whitespace-delimited words.
        """
        if len(value.split()) < 2:
            raise ValueError("query must contain at least two words")
        return value
