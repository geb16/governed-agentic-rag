"""Provide secondary faithfulness grading through pinned Ragas 0.4 APIs.

The adapter connects an asynchronous OpenAI client to Ragas and measures whether
response claims are supported by retrieved context. Results are diagnostic and do
not replace registered human adjudication.

References:
    [1] OpenAI, "OpenAI Python API library," Async usage.
        https://github.com/openai/openai-python#async-usage
    [2] Ragas, "LLMs," llm_factory.
        https://docs.ragas.io/en/stable/references/llms/
    [3] Ragas, "Faithfulness."
        https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness


class RagasFaithfulnessGrader:
    """Evaluates response faithfulness with an asynchronous OpenAI model.

    Unless already configured by the environment, construction disables Ragas
    telemetry. The supplied client is wrapped by llm_factory and bound to one
    Faithfulness metric instance. OpenAI and Ragas failures propagate so an
    unavailable grade cannot be mistaken for a valid result.

    Args:
        api_key: Credential passed directly to AsyncOpenAI.
        model: OpenAI model identifier passed to the Ragas LLM factory.
    """

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
        """Scores whether response claims are supported by retrieved contexts.

        Args:
            query: User request that elicited the response.
            response: Generated answer to evaluate.
            contexts: Retrieved passages offered as supporting evidence.

        Returns:
            A (score, reason) pair. Score is the Ragas faithfulness value in the
            range zero to one; reason is empty when Ragas provides none.
        """
        result = await self._metric.ascore(
            user_input=query,
            response=response,
            retrieved_contexts=contexts,
        )
        return float(result.value), result.reason or ""
