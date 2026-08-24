import hashlib
import hmac
import json
from typing import Any


def canonical_digest(value: Any, *, key: bytes | None = None) -> str:
    """Return a stable SHA-256 or HMAC-SHA-256 digest for JSON-compatible data."""

    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if key is not None:
        return hmac.new(key, encoded, hashlib.sha256).hexdigest()
    return hashlib.sha256(encoded).hexdigest()
