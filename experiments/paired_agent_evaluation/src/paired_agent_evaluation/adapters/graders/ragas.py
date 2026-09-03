"""Pinned Ragas 0.4 secondary faithfulness adapter."""

from __future__ import annotations

import os

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness


class RagasFaithfulnessGrader:
    """Return a diagnostic score; never substitute for registered human review."""

    def __init__(self, *, api_key: str, model: str) -> None:
        os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
        client = AsyncOpenAI(api_key=api_key)
        self._metric = Faithfulness(llm=llm_factory(model, client=client))

    async def grade(
        self,
        *,
        query: str,
        response: str,
        contexts: list[str],
    ) -> tuple[float, str]:
        result = await self._metric.ascore(
            user_input=query,
            response=response,
            retrieved_contexts=contexts,
        )
        return float(result.value), result.reason or ""
