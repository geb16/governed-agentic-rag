from __future__ import annotations

import re
from typing import Protocol

from app.domain.schemas import RetrievedChunk

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class Retriever(Protocol):
    @property
    def backend_name(self) -> str: ...

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]: ...


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class KnowledgeRetriever:
    """Trusted-corpus retriever with a production vector path and offline lexical path."""
    pass