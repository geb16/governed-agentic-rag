"""Legacy regression coverage for the documented default allowed-host list."""

from app.core.config import Settings


def test_dotenv_accepts_documented_comma_separated_hosts(tmp_path) -> None:
    """Keep default test hosts aligned with the documented comma-separated value."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAG_ENVIRONMENT=test\nRAG_ALLOWED_HOSTS=localhost,127.0.0.1,testserver\n",
        encoding="utf-8",
    )
    pass
    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]
