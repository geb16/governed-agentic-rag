from __future__ import annotations

import hashlib
import json
from typing import Any

from app.domain.schemas import EvidenceReference, EvidenceType


# function to create an EvidenceReference object with a SHA-256 hash
# of the canonical JSON representation of the payload.
def evidence_reference(
    *,
    evidence_id: str,
    evidence_type: EvidenceType,
    source_id: str,
    title: str,
    payload: dict[str, Any],
    score: float | None = None,
) -> EvidenceReference:
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return EvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_id=source_id,
        title=title,
        content_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        score=score,
    )
