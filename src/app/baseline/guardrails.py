from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.domain.schemas import AgentDraft

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
    (
        "prompt_extraction",
        re.compile(
            r"(?is)\b(reveal|repeat|print|show|expose)\b.{0,40}\b"
            r"(system prompt|hidden instruction|developer message|internal prompt)s?\b"
        ),
    ),
    (
        "control_bypass",
        re.compile(
            r"(?is)\b(bypass|disable|override|evade)\b.{0,40}\b"
            r"(guardrail|safety|security|policy control|tool restriction)s?\b"
        ),
    ),
    (
        "encoded_injection",
        re.compile(r"SWdub3JlIGFsbCBwcmV2aW91cyBpbnN0cnVjdGlvbnM", re.IGNORECASE),
    ),
)

_OUTPUT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("active_content", re.compile(r"(?is)<\s*(script|iframe|object|img)\b")),
    (
        "secret_like_output",
        re.compile(r"(?i)\b(api[_-]?key|password|secret|bearer token)\s*[=:]\s*\S+"),
    ),
    (
        "prompt_leakage",
        re.compile(r"(?is)\b(system prompt|developer message)\b.{0,20}\b(is|says|contains)\b"),
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


class OutputGuardrail:
    def inspect(
        self,
        draft: AgentDraft,
        *,
        allowed_chunk_ids: set[str],
    ) -> GuardrailDecision:
        if len(set(draft.cited_chunk_ids)) != len(draft.cited_chunk_ids):
            return GuardrailDecision(True, "duplicate_citation")
        if not set(draft.cited_chunk_ids).issubset(allowed_chunk_ids):
            return GuardrailDecision(True, "fabricated_citation")
        if draft.grounded and not draft.cited_chunk_ids:
            return GuardrailDecision(True, "missing_citation")
        for category, pattern in _OUTPUT_RULES:
            if pattern.search(draft.answer):
                return GuardrailDecision(True, category)
        return GuardrailDecision(False, normalized_text=draft.answer)
