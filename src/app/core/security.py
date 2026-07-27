import hashlib
import hmac


def stable_safety_identifier(requester_id: str, secret: str) -> str:
    """Create a keyed pseudonymous identifier; never send raw enterprise identity upstream."""

    return hmac.new(
        secret.encode("utf-8"),
        requester_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
