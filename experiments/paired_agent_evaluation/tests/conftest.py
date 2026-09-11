from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.core.config import Settings
from app.domain.evidence import RetrievedChunk
from app.domain.model import AgentDraft, ModelTurn
from app.evaluation.dataset.enums import DatasetSplit
from app.evaluation.dataset.models import EvaluationCase
from app.governance.contracts import (
    ClassificationDraft,
    GovernedFinalDraft,
    ProposedActionDraft,
    ProposedActionKind,
    Sensitivity,
    TaskIntent,
    TaskType,
)
from app.governance.llm import ModelResult

from paired_agent_evaluation.adapters.dataset import EvaluationDataset
from paired_agent_evaluation.composition import EvaluationPaths


class StaticRetriever:
    backend_name = "qdrant"

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="policy:test:0",
                document_id="support_policy",
                title="Support policy",
                content="Support agents may answer approved policy questions.",
                source_path="synthetic.md",
                score=1.0,
                content_sha256="a" * 64,
            )
        ]


class BaselineAnswerModel:
    model_name = "fixed-test-model"

    def complete(self, **_: Any) -> ModelTurn:
        return ModelTurn(
            final=AgentDraft(
                answer="Support agents may answer approved policy questions.",
                cited_chunk_ids=["policy:test:0"],
                grounded=True,
            ),
            input_tokens=5,
            output_tokens=3,
        )


class GovernedAnswerModel:
    model_name = "fixed-test-model"

    def classify(self, *_: Any, **__: Any) -> ModelResult[ClassificationDraft]:
        return ModelResult(
            ClassificationDraft(
                intent=TaskIntent.INFORMATION,
                task_type=TaskType.READ_ONLY,
                sensitivity=Sensitivity.LOW,
                confidence=1.0,
                summary="Read-only policy question.",
            ),
            input_tokens=2,
            output_tokens=1,
        )

    def propose(self, *_: Any, **__: Any) -> ModelResult[ProposedActionDraft]:
        return ModelResult(
            ProposedActionDraft(
                kind=ProposedActionKind.RESPOND,
                response_text="A supported response is available.",
                confidence=1.0,
                rationale="Retrieved policy answers the request.",
            ),
            input_tokens=2,
            output_tokens=1,
        )

    def finalize(self, *_: Any, **__: Any) -> ModelResult[GovernedFinalDraft]:
        return ModelResult(
            GovernedFinalDraft(
                answer="Support agents may answer approved policy questions.",
                cited_evidence_ids=["policy:test:0"],
                grounded=True,
            ),
            input_tokens=2,
            output_tokens=1,
        )


@pytest.fixture
def paths() -> EvaluationPaths:
    return EvaluationPaths.discover()


@pytest.fixture
def answer_case(paths: EvaluationPaths) -> EvaluationCase:
    cases = EvaluationDataset(paths.repository).cases(DatasetSplit.VALIDATION)
    return next(case for case in cases if case.expected.route.value == "answer")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        execution_profile="test",
        retrieval_backend="lexical",
        synthetic_database_path=tmp_path / "unused.db",
    )
