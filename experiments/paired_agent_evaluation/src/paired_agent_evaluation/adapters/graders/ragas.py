"""Provides secondary faithfulness grading through pinned Ragas 0.4 APIs.

The adapter evaluates whether a response is supported by its retrieved
contexts. Scores are diagnostic supplements to the registered human review and
must not be used as replacements for primary adjudication.
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness


class RagasFaithfulnessGrader:
    """Evaluates response faithfulness with a configured language model.

    The grader disables Ragas telemetry by default and delegates asynchronous
    evaluation to the Ragas ``Faithfulness`` metric. Provider and metric errors
    are allowed to propagate so callers cannot mistake a failed grade for a
    valid score.

    Args:
        api_key: OpenAI API key used by the asynchronous model client.
        model: Model identifier passed to the Ragas language-model factory.
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
        """Scores how faithfully a response reflects its retrieved contexts.

        Args:
            query: User request that elicited the response.
            response: Generated answer to evaluate.
            contexts: Retrieved passages offered as supporting evidence.

        Returns:
            A pair containing the numeric faithfulness score and the grader's
            rationale. The rationale is an empty string when Ragas omits it.
        """
        result = await self._metric.ascore(
            user_input=query,
            response=response,
            retrieved_contexts=contexts,
        )
        return float(result.value), result.reason or ""
