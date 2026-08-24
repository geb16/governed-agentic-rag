"""Phase 4 principal binding and security-configuration tests."""

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import stable_safety_identifier
from app.governance.security import GovernanceSecuritySettings, IdentityService


def test_governance_roles_parse_and_normalize() -> None:
    """Support deployable environment syntax while keeping role bindings deterministic."""

    settings = GovernanceSecuritySettings.model_validate(
        {"approval_roles": "fraud_reviewer, finance_manager"}
    )

    assert settings.approval_roles == ["finance_manager", "fraud_reviewer"]


def test_governance_security_loads_documented_dotenv_values(tmp_path, monkeypatch) -> None:
    """Load the Phase 4 principal, roles, and audit key from the documented dotenv source."""

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "RAG_GOVERNANCE_APPROVAL_PRINCIPAL_ID=local-reviewer",
                "RAG_GOVERNANCE_APPROVAL_ROLES=fraud_reviewer,finance_manager",
                f"RAG_GOVERNANCE_AUDIT_INTEGRITY_KEY={'a' * 32}",
            )
        ),
        encoding="utf-8",
    )
    for name in (
        "RAG_GOVERNANCE_APPROVAL_PRINCIPAL_ID",
        "RAG_GOVERNANCE_APPROVAL_ROLES",
        "RAG_GOVERNANCE_AUDIT_INTEGRITY_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)

    settings = GovernanceSecuritySettings()

    assert settings.approval_principal_id == "local-reviewer"
    assert settings.approval_roles == ["finance_manager", "fraud_reviewer"]
    assert settings.resolve_audit_key(development_fallback=b"fallback") == b"a" * 32


def test_production_requires_at_least_one_approval_role() -> None:
    """Prevent a production workflow that can pause but can never authorize a resume."""

    with pytest.raises(ValueError, match="APPROVAL_ROLES"):
        GovernanceSecuritySettings.model_validate({"approval_roles": []}).validate_runtime(
            production=True,
            experiment=False,
        )


def test_controlled_runtime_requires_a_dedicated_audit_key() -> None:
    """Keep audit verification stable when an API credential rotates."""

    settings = GovernanceSecuritySettings.model_validate(
        {
            "approval_roles": ["finance_manager"],
            "audit_integrity_key": None,
        }
    )
    with pytest.raises(ValueError, match="AUDIT_INTEGRITY_KEY"):
        settings.validate_runtime(production=True, experiment=False)
    with pytest.raises(ValueError, match="AUDIT_INTEGRITY_KEY"):
        settings.validate_runtime(production=False, experiment=True)

    configured = GovernanceSecuritySettings(
        approval_roles=["finance_manager"],
        audit_integrity_key=SecretStr("a" * 32),
    )
    configured.validate_runtime(production=True, experiment=False)
    assert configured.resolve_audit_key(development_fallback=b"fallback") == b"a" * 32


def test_identity_uses_only_the_dedicated_safety_secret() -> None:
    """Keep pseudonyms stable across authentication and provider-key rotation."""

    settings = Settings(
        environment="test",
        api_key=SecretStr("inbound-authentication-key"),
        openai_api_key=SecretStr("provider-credential"),
        safety_identifier_secret=SecretStr("dedicated-identity-secret"),
    )
    identity = IdentityService(settings)

    pseudonym = identity.pseudonym("reviewer-123")

    assert pseudonym == stable_safety_identifier(
        "reviewer-123",
        "dedicated-identity-secret",
    )
    assert pseudonym != stable_safety_identifier(
        "reviewer-123",
        "inbound-authentication-key",
    )
    assert pseudonym != stable_safety_identifier("reviewer-123", "provider-credential")
