"""Load Phase 4 security settings outside the frozen Phase 3 control.

The model binds the pilot API credential to a server-configured approval principal,
normalizes trusted roles, and resolves a dedicated audit-integrity key. Environment
values use the ``RAG_GOVERNANCE_`` prefix and may be loaded from ``.env`` locally.
"""

from __future__ import annotations

import json
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class GovernanceSecuritySettings(BaseSettings):
    """Bind the configured API credential to one approval principal and its roles.

    This deliberately small pilot model treats the application's existing API key as
    one service principal. Callers cannot submit or override the authenticated subject.
    A production identity provider can later replace this adapter without changing the
    workflow contracts.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        env_prefix="RAG_GOVERNANCE_",
        case_sensitive=False,
        extra="ignore",
    )

    approval_principal_id: str = Field(default="local-governance-reviewer", min_length=2)
    approval_roles: Annotated[list[str], NoDecode] = Field(default_factory=list)
    audit_integrity_key: SecretStr | None = Field(default=None, min_length=32)

    @field_validator("approval_roles", mode="before")
    @classmethod
    def parse_roles(cls, value: object) -> object:
        """Parse approval roles from JSON or comma-separated environment syntax.

        Args:
            value: Raw Pydantic Settings input.

        Returns:
            A list for string input, otherwise the original value.

        Raises:
            ValueError: If JSON input is valid JSON but is not an array.
        """
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if stripped.startswith("["):
            decoded = json.loads(stripped)
            if not isinstance(decoded, list):
                raise ValueError("approval_roles JSON value must be an array")
            return decoded
        return [item.strip() for item in stripped.split(",") if item.strip()]

    @field_validator("approval_roles")
    @classmethod
    def normalize_roles(cls, roles: list[str]) -> list[str]:
        """Reject unsafe role bindings and return deterministic ordering.

        Args:
            roles: Parsed server-side role names.

        Returns:
            Trimmed unique roles sorted for reproducible decisions and manifests.

        Raises:
            ValueError: If any role is blank or appears more than once.
        """
        normalized = [role.strip() for role in roles]
        if any(not role for role in normalized):
            raise ValueError("approval roles must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("approval roles must be unique")
        return sorted(normalized)

    def validate_runtime(self, *, production: bool, experiment: bool) -> None:
        """Fail controlled runtimes with incomplete governance security.

        Args:
            production: Whether the deployment is production-facing.
            experiment: Whether execution contributes controlled research data.

        Raises:
            ValueError: If production has no approval roles or a controlled runtime
                lacks an independent audit-integrity key.
        """
        if production and not self.approval_roles:
            raise ValueError("RAG_GOVERNANCE_APPROVAL_ROLES is required in production")
        if (production or experiment) and self.audit_integrity_key is None:
            raise ValueError(
                "RAG_GOVERNANCE_AUDIT_INTEGRITY_KEY is required in production and experiments"
            )

    def resolve_audit_key(self, *, development_fallback: bytes) -> bytes:
        """Resolve the key used to authenticate the audit hash chain.

        Args:
            development_fallback: Purpose-derived key allowed only after runtime
                validation has established a non-controlled profile.

        Returns:
            The configured dedicated key, or the supplied development fallback.
        """
        if self.audit_integrity_key is None:
            return development_fallback
        return self.audit_integrity_key.get_secret_value().encode("utf-8")
