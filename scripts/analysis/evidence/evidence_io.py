"""Read, verify, and write deterministic Phase 7 evidence files."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence.evidence_config import GENERATED_FILENAMES, RELEASE_ID, RELEASE_SHA256

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ReleaseData:
    """Hold the sealed inputs consumed by the Phase 7 evidence pipeline.

    Attributes:
        manifest: Release manifest and content-addressed file inventory.
        estimates: Condition-level metric estimates.
        differences: Paired governed-minus-baseline effects.
        summary: Aggregate run and token-usage statistics.
        normalized: Normalized observations used by primary scoring.
        scores: Observation-level primary metric contributions.
        ragas: Observation-level secondary Ragas results.

    """

    manifest: JsonObject
    estimates: list[JsonObject]
    differences: list[JsonObject]
    summary: JsonObject
    normalized: list[JsonObject]
    scores: list[JsonObject]
    ragas: list[JsonObject]


def sha256(path: Path) -> str:
    """Calculate the SHA-256 digest of a file.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.

    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_release(release: Path) -> ReleaseData:
    """Verify the sealed release and load every analysis input.

    Args:
        release: Directory containing the canonical sealed release.

    Returns:
        Verified release inputs required by the evidence generators.

    Raises:
        ValueError: If the release identity or a sealed file digest differs
            from the approved manifest.

    """
    manifest = _load_json(release / "manifest.json")
    _verify_manifest(release, manifest)
    return ReleaseData(
        manifest=manifest,
        estimates=_load_json(release / "estimates.json"),
        differences=_load_json(release / "paired-differences.json"),
        summary=_load_json(release / "summary.json"),
        normalized=_load_jsonl(release / "normalized.jsonl"),
        scores=_load_jsonl(release / "scores.jsonl"),
        ragas=_load_jsonl(release / "secondary-ragas.jsonl"),
    )


def write_csv(path: Path, headings: list[str], rows: list[list[Any]]) -> None:
    """Write a CSV with stable newlines and column order.

    Args:
        path: Destination path for the CSV file.
        headings: Column headings in publication order.
        rows: Data rows matching the heading order.

    """
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(headings)
        writer.writerows(rows)


def write_provenance(
    output: Path,
    manifest: JsonObject,
    generator: Path,
    repository: Path,
) -> int:
    """Hash generated evidence and write its source provenance manifest.

    Args:
        output: Directory containing the generated evidence set.
        manifest: Verified source-release manifest.
        generator: Evidence entry point to record in provenance.
        repository: Repository root used to make source paths relative.

    Returns:
        Number of generated evidence files recorded in provenance.

    Raises:
        ValueError: If the generated evidence set has missing or unmanaged files.

    """
    expected = {*GENERATED_FILENAMES, "provenance.json"}
    actual = {path.name for path in output.iterdir()}
    if unexpected := sorted(actual - expected):
        raise ValueError(f"Unmanaged generated evidence: {', '.join(unexpected)}")
    if missing := sorted(set(GENERATED_FILENAMES) - actual):
        raise ValueError(f"Missing generated evidence: {', '.join(missing)}")

    generated = [output / name for name in GENERATED_FILENAMES]
    analysis_sources = sorted(generator.parent.rglob("*.py"))
    provenance = {
        "schema_version": 1,
        "source_release_id": manifest["release_id"],
        "source_release_aggregate_sha256": manifest["aggregate_sha256"],
        "source_run_id": manifest["run_id"],
        "generator": str(generator.relative_to(repository)),
        "analysis_sources": {
            str(path.relative_to(repository)): sha256(path) for path in analysis_sources
        },
        "generated_files": {path.name: sha256(path) for path in generated},
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return len(generated)


def _load_json(path: Path) -> Any:
    """Load and return one UTF-8 JSON document."""
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _load_jsonl(path: Path) -> list[JsonObject]:
    """Load nonblank records from a UTF-8 JSON Lines file."""
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _verify_manifest(release: Path, manifest: JsonObject) -> None:
    """Validate the release identity and every manifest-listed file digest.

    Raises:
        ValueError: If the release is not approved or any file digest differs.

    """
    if manifest["release_id"] != RELEASE_ID or manifest["aggregate_sha256"] != RELEASE_SHA256:
        raise ValueError("The source is not the approved sealed Phase 6 release")
    for relative, expected in manifest["files"].items():
        actual = sha256(release / relative)
        if actual != expected:
            raise ValueError(f"Sealed source digest mismatch: {relative}")
