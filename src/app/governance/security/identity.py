"""Provide purpose-separated pseudonyms and derived development integrity keys.

Raw enterprise identities must not cross into model or audit records. Controlled
profiles require the shared safety-identifier secret through core configuration;
only development and test may use the explicit non-production fallback.
"""

import hashlib
import hmac

from app.core.config import Settings
from app.core.security import stable_safety_identifier


class IdentityService:
    """Pseudonymize identities and derive purpose-bound keys from one root secret.

    Args:
        settings: Validated shared settings containing the dedicated safety secret.

    Note:
        The fallback is deterministic solely for non-controlled local execution.
        Experiment and production validation requires a configured secret.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize identity protection with configured or local fallback secret."""
        self._secret = (
            settings.safety_identifier_secret.get_secret_value()
            if settings.safety_identifier_secret is not None
            else "governed-development-only"
        )

    def pseudonym(self, actor_id: str) -> str:
        """Return a stable HMAC pseudonym for a trusted actor identity.

        Args:
            actor_id: Internal authenticated subject identifier.

        Returns:
            A lowercase keyed digest safe to persist or send to a provider.
        """
        return stable_safety_identifier(actor_id, self._secret)

    def derive_key(self, purpose: str) -> bytes:
        """Derive a purpose-bound integrity key without exposing the root secret.

        Args:
            purpose: Stable context label separating one derived-key use from another.

        Returns:
            A 32-byte HMAC-SHA-256 derived key.
        """
        return hmac.new(
            self._secret.encode("utf-8"),
            purpose.encode("utf-8"),
            hashlib.sha256,
        ).digest()
