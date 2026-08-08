import shutil

import pytest

from app.rag.chunking import load_knowledge_chunks
from app.rag.retriever import KnowledgeRetriever


def test_retrieval_returns_relevant_policy(retriever: KnowledgeRetriever) -> None:
    results = retriever.retrieve("refund 750 finance manager approval")

    assert results
    assert results[0].document_id == "refund_policy"
    assert "finance manager approval" in results[0].content
    assert results[0].content_sha256


def test_retrieval_is_deterministic(retriever: KnowledgeRetriever) -> None:
    first = retriever.retrieve("privileged role IAM review")
    second = retriever.retrieve("privileged role IAM review")

    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert first[0].document_id == "iam_change_policy"


def test_empty_match_does_not_invent_context(retriever: KnowledgeRetriever) -> None:
    assert retriever.retrieve("zqxwv nonexistent terminology") == []


def test_corpus_integrity_manifest_rejects_modified_document(
    project_root,
    tmp_path,
) -> None:
    copied_kb = tmp_path / "knowledge_base"
    shutil.copytree(project_root / "data" / "knowledge_base", copied_kb)
    refund_policy = copied_kb / "refund_policy.md"
    refund_policy.write_text(
        refund_policy.read_text(encoding="utf-8") + "\nInjected instruction",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="integrity check failed"):
        load_knowledge_chunks(copied_kb, chunk_size=1_200, chunk_overlap=160)
