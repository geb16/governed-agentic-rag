"""Governance-neutral evidence, citation, and retrieval contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.domain.contracts import StrictModel


class EvidenceType(StrEnum):
    """Origins supported by the governance-neutral evidence contract."""

    KNOWLEDGE_CHUNK = "knowledge_chunk"
    TOOL_RESULT = "tool_result"
    BUSINESS_RECORD = "business_record"


class EvidenceReference(StrictModel):
    """Stable metadata identifying evidence without embedding its full content."""

    evidence_id: str = Field(min_length=1, max_length=300)
    evidence_type: EvidenceType
    source_id: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    content_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class Citation(StrictModel):
    """Caller-facing citation to an approved retrieved knowledge chunk."""

    chunk_id: str
    document_id: str
    title: str
    score: float = Field(ge=0.0, le=1.0)


class RetrievedChunk(StrictModel):
    """Ranked and integrity-addressed unit of approved knowledge."""

    chunk_id: str
    document_id: str
    title: str
    content: str
    source_path: str
    score: float = Field(ge=0.0, le=1.0)
    content_sha256: str
