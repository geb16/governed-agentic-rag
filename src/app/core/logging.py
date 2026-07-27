from __future__ import annotations

import logging
import re
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


class JsonFormatter(logging.Formatter):
   pass


def configure_logging(settings: Settings) -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


