"""Run optional asynchronous Ragas grading as a secondary diagnostic.

References:
    [1] Ragas, "Faithfulness."
        https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
    [2] Python Software Foundation, "asyncio — Asynchronous I/O."
        https://docs.python.org/3/library/asyncio.html
"""

from __future__ import annotations

import asyncio
import json

from app.core.config import Settings

from paired_agent_evaluation.adapters.storage.filesystem import JsonlStore, RawFilesystemStore
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.scores import SecondaryGrade


async def _grade_ragas(run_id: str) -> list[SecondaryGrade]:
    """Grades answer-bearing executions against retrieved context with Ragas.

    Executions without both an answer and context are excluded. These diagnostic
    grades do not alter primary metric artifacts.

    Raises:
        ValueError: If the secondary grader API key is unavailable.
    """
    from paired_agent_evaluation.adapters.graders import RagasFaithfulnessGrader

    paths = EvaluationPaths.discover()
    run_root = paths.run_root(run_id)
    raw = RawFilesystemStore(run_root / "raw" / "observations").read_all()
    manifest = json.loads((run_root / "run-manifest.json").read_text(encoding="utf-8"))
    settings = Settings(
        _env_file=paths.repository / ".env"  # pyright: ignore[reportCallIssue]
    )
    if settings.openai_api_key is None:
        raise ValueError("RAG_OPENAI_API_KEY is required for secondary Ragas grading")
    grader = RagasFaithfulnessGrader(
        api_key=settings.openai_api_key.get_secret_value(),
        model=str(manifest["model_identifier"]),
    )
    grades = []
    for execution in raw:
        answer = str((execution.response or {}).get("answer") or "")
        contexts = [item.content for item in execution.retrieved]
        if not answer or not contexts:
            continue
        value, reason = await grader.grade(
            query=str(execution.request["query"]),
            response=answer,
            contexts=contexts,
        )
        grades.append(
            SecondaryGrade(
                observation_id=execution.key.observation_id,
                grader="ragas.Faithfulness",
                grader_version="0.4.3",
                model_identifier=str(manifest["model_identifier"]),
                value=value,
                reason=reason,
            )
        )
    JsonlStore.write(run_root / "secondary-ragas.jsonl", grades)
    return grades


def grade_ragas(*, run_id: str) -> list[SecondaryGrade]:
    """Runs asynchronous secondary Ragas grading from synchronous code."""
    return asyncio.run(_grade_ragas(run_id))
