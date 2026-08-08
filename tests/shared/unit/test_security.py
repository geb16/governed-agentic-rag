import json
import logging

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings
from app.core.logging import JsonFormatter
from app.core.security import stable_safety_identifier


def test_safety_identifier_is_keyed_and_does_not_expose_identity() -> None:
    first = stable_safety_identifier("employee@example.test", "secret-a")
    second = stable_safety_identifier("employee@example.test", "secret-b")

    assert first != second
    assert "employee" not in first
    assert len(first) == 64


def test_json_logging_redacts_secrets_and_log_injection() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="authorization=Bearer-value\nforged-line",
        args=(),
        exc_info=None,
    )
    record.context = {"password": "do-not-log", "trace_id": "trace_1"}  # type: ignore[attr-defined]

    payload = json.loads(formatter.format(record))

    assert "Bearer-value" not in payload["message"]
    assert "\n" not in payload["message"]
    assert payload["context"]["password"] == "[REDACTED]"
    assert payload["context"]["trace_id"] == "trace_1"


def test_production_rejects_plaintext_qdrant(project_root) -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            environment="production",
            api_key=SecretStr("inbound"),
            openai_api_key=SecretStr("openai"),
            retrieval_backend="qdrant",
            qdrant_url="http://qdrant.internal:6333",
            qdrant_read_api_key=SecretStr("read-only"),
            knowledge_base_dir=project_root / "data" / "knowledge_base",
        )
