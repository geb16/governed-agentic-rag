from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings

_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|authorization|password|secret|token)(\s*[=:]\s*)([^\s,;]+)"
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)^(api[_-]?key|authorization|password|secret|access[_-]?token|refresh[_-]?token)$"
)


# Redact sensitive information in logs and JSON output
def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if _SECRET_KEY_PATTERN.search(str(key)) else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        escaped = value.replace("\r", "\\r").replace("\n", "\\n")
        return _SECRET_PATTERN.sub(r"\1\2[REDACTED]", escaped)
    return value

# Custom JSON formatter for logging
class JsonFormatter(logging.Formatter):
    """One-line JSON logs suitable for collection without recording prompt bodies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = _redact(context)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(_redact(payload), ensure_ascii=True, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

