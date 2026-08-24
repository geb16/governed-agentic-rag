"""Create deterministic, non-secret digests for proposal binding.

Proposal digests detect substitution between risk review, approval, and execution.
They are identifiers rather than authentication tags and must not replace the keyed
hash chain used for audit integrity.
"""

import hashlib
import json
from typing import Any


def proposal_digest(value: Any) -> str:
    """Return a canonical SHA-256 identity for a proposal-like value.

    Args:
        value: Pydantic model or JSON-serializable proposal representation.

    Returns:
        A lowercase hexadecimal digest over sorted, compact JSON.

    Note:
        The digest contains no secret key. Its security purpose is stable proposal
        binding, not proof of authorship or storage integrity.
    """
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
