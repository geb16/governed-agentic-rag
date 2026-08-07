"""Canonical integrity references for structured tool evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.domain.schemas import EvidenceReference, EvidenceType


def evidence_reference(
    *,
    evidence_id: str,
    evidence_type: EvidenceType,
    source_id: str,
    title: str,
    payload: dict[str, Any],
    score: float | None = None,
) -> EvidenceReference:
    """Create an evidence reference from the canonical SHA-256 of a payload.

    Args:
        evidence_id: Invocation-unique evidence identifier.
        evidence_type: Controlled origin category.
        source_id: Stable business or tool-result identifier.
        title: Human-readable evidence label.
        payload: Structured evidence content to integrity-address.
        score: Optional bounded retrieval score.

    Returns:
        Evidence metadata containing the canonical payload digest.
    """
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return EvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_id=source_id,
        title=title,
        content_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        score=score,
    )
