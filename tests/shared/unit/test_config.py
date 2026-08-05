from app.core.config import Settings


def test_dotenv_accepts_documented_comma_separated_hosts(monkeypatch) -> None:
    monkeypatch.setenv("RAG_ENVIRONMENT", "test")
    monkeypatch.setenv("RAG_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "127.0.0.1", "testserver"]


def test_dotenv_also_accepts_json_host_array(monkeypatch) -> None:
    monkeypatch.setenv("RAG_ENVIRONMENT", "test")
    monkeypatch.setenv("RAG_ALLOWED_HOSTS", '["localhost","testserver"]')

    settings = Settings()

    assert settings.allowed_hosts == ["localhost", "testserver"]
