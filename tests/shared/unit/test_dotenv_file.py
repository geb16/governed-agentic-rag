"""File-backed configuration contracts for the documented allowed-host formats."""

from app.core.config import Settings


def test_dotenv_accepts_documented_comma_separated_hosts(tmp_path, monkeypatch) -> None:
    """Parse comma-separated hosts from an isolated dotenv file.

    Process-level overrides are removed before ``Settings`` is constructed so the assertion proves
    that the configured ``.env`` source, rather than a developer's environment, supplies the value.
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAG_ENVIRONMENT=test\nRAG_ALLOWED_HOSTS=localhost,127.0.0.1,testserver\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("RAG_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAG_ALLOWED_HOSTS", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]
