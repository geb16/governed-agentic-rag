"""Unit contracts for supported allowed-host environment encodings."""

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_dotenv_accepts_documented_comma_separated_hosts(monkeypatch) -> None:
    """Parse a comma-separated allowed-host environment value."""
    monkeypatch.setenv("RAG_ENVIRONMENT", "test")
    monkeypatch.setenv("RAG_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]


def test_dotenv_also_accepts_json_host_array(monkeypatch) -> None:
    """Parse a JSON-array allowed-host environment value."""
    monkeypatch.setenv("RAG_ENVIRONMENT", "test")
    monkeypatch.setenv("RAG_ALLOWED_HOSTS", '["localhost","testserver"]')

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "testserver"]


def test_experiment_profile_requires_dedicated_safety_identifier_secret() -> None:
    """Reject experiments that would pseudonymize identities with a fallback key."""
    with pytest.raises(ValidationError, match="requires RAG_SAFETY_IDENTIFIER_SECRET"):
        Settings(
            execution_profile="experiment",
            retrieval_backend="qdrant",
            qdrant_url="http://127.0.0.1:6333",
            openai_api_key=SecretStr("provider-key"),
            safety_identifier_secret=None,
            experiment_run_id="run_missing_safety_secret",
        )


def test_production_requires_dedicated_safety_identifier_secret() -> None:
    """Keep provider pseudonymization independent of inbound authentication."""
    with pytest.raises(ValidationError, match="required in production"):
        Settings(
            environment="production",
            api_key=SecretStr("inbound-key"),
            openai_api_key=SecretStr("provider-key"),
            safety_identifier_secret=None,
            allowed_hosts=["service.example.test"],
        )
