from app.core.config import Settings


# Test to ensure that the Settings class correctly parses comma-separated allowed hosts
def test_dotenv_accepts_documented_comma_separated_hosts(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAG_ENVIRONMENT=test\nRAG_ALLOWED_HOSTS=localhost,127.0.0.1,testserver\n",
        encoding="utf-8",
    )
    pass
    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]
