from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_INPUT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "prompt_injection",
        re.compile(
            r"(?is)\b(ignore|disregard|forget)\b.{0,40}\b"
            r"(previous|prior|system|developer|security|safety)\b.{0,30}\b"
            r"(instruction|message|rule|control)s?\b"
        ),
    ),
)

@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    blocked: bool
    category: str | None = None
    normalized_text: str = ""


class InputGuardrail:
    """Deterministic first-line screening; prompt instructions remain a second layer."""

    def inspect(self, text: str, *, max_chars: int) -> GuardrailDecision:
        normalized = unicodedata.normalize("NFKC", text).strip()
        if len(normalized) > max_chars:
            return GuardrailDecision(True, "input_too_large")
        if _CONTROL_CHARS.search(normalized):
            return GuardrailDecision(True, "control_characters")
        for category, pattern in _INPUT_RULES:
            if pattern.search(normalized):
                return GuardrailDecision(True, category)
        return GuardrailDecision(False, normalized_text=normalized)


