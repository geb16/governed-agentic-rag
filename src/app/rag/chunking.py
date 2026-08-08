from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_DOCUMENT_BYTES = 512_000  # Set 512 KB to avoid excessive memory usage


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    title: str
    content: str
    source_path: str
    content_sha256: str


def _windows(text: str, size: int, overlap: int) -> list[str]:
    if not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind("\n", start + (size // 2), end)
            if boundary > start:
                end = boundary
        part = text[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


# validating the knowledge base files and loading them into chunks
def _safe_markdown_files(base_dir: Path) -> list[Path]:

    resolved_base = base_dir.resolve(strict=True)
    manifest_path = resolved_base / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Knowledge-base manifest is missing: {manifest_path}")
    manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("documents"), dict)
    ):
        raise ValueError("Knowledge-base manifest is invalid")
    expected: dict[str, str] = manifest["documents"]
    files: list[Path] = []
    for candidate in sorted(resolved_base.glob("*.md")):
        resolved = candidate.resolve(strict=True)
        if resolved.parent != resolved_base:
            raise ValueError(f"Knowledge document escapes configured directory: {candidate}")
        if resolved.stat().st_size > MAX_DOCUMENT_BYTES:
            raise ValueError(f"Knowledge document exceeds size limit: {candidate.name}")
        expected_hash = expected.get(candidate.name)
        actual_hash = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if expected_hash is None or not isinstance(expected_hash, str):
            raise ValueError(f"Knowledge document is not allowlisted: {candidate.name}")
        if actual_hash != expected_hash:
            raise ValueError(f"Knowledge document integrity check failed: {candidate.name}")
        files.append(resolved)
    if {path.name for path in files} != set(expected):
        raise ValueError("Knowledge-base manifest does not match the document set")
    return files


def load_knowledge_chunks(
    base_dir: Path,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for path in _safe_markdown_files(base_dir):
        raw = path.read_text(encoding="utf-8")
        title = next(
            (line.lstrip("#").strip() for line in raw.splitlines() if line.startswith("#")),
            path.stem.replace("_", " ").title(),
        )
        document_id = path.stem.lower()
        for index, content in enumerate(_windows(raw, chunk_size, chunk_overlap), start=1):
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{document_id}:{index}:{digest[:12]}",
                    document_id=document_id,
                    title=title,
                    content=content,
                    source_path=path.name,
                    content_sha256=digest,
                )
            )
    if not chunks:
        raise ValueError(f"No Markdown knowledge documents found in {base_dir}")
    return chunks
