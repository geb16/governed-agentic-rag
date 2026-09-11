"""Independently verify primary results and sealed release integrity.

References:
    [1] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
    [2] NIST, "FIPS 180-4: Secure Hash Standard."
        https://doi.org/10.6028/NIST.FIPS.180-4
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from paired_agent_evaluation.adapters.storage.filesystem import canonical_json
from paired_agent_evaluation.composition import EvaluationPaths
from paired_agent_evaluation.domain.manifests import ExperimentManifest, ReleaseManifest
from paired_agent_evaluation.release.artifacts import json_value, read_payload, sha256_file
from paired_agent_evaluation.reporting import derive_primary_artifacts
from paired_agent_evaluation.reporting.visual_report import render_html_report


def verify_primary_artifacts(run_root: Path, manifest: ExperimentManifest) -> None:
    """Verifies stored primary results against an independent derivation.

    The HTML report is regenerated from authoritative derived data; structured
    artifacts are compared semantically.

    Raises:
        ValueError: If a stored artifact differs from its derivation.
        OSError: If a required artifact cannot be read.
    """
    expected = derive_primary_artifacts(
        paths=EvaluationPaths.discover(),
        run_root=run_root,
        manifest=manifest,
    )
    drift = [
        name
        for name, payload in expected.items()
        if read_payload(run_root / name) != json_value(payload)
    ]
    report_inputs = {"summary.json", "estimates.json", "paired-differences.json"}
    if report_inputs <= expected.keys():
        expected_report = render_html_report(
            expected["summary.json"],
            expected["estimates.json"],
            expected["paired-differences.json"],
        )
        if read_payload(run_root / "report.html") != expected_report:
            drift.append("report.html")
    if drift:
        raise ValueError(f"Primary derived artifacts have changed: {', '.join(drift)}")


def verify_release(release_root: Path) -> ReleaseManifest:
    """Verifies the closed file set and all release content digests.

    Returns:
        The validated release manifest.

    Raises:
        ValueError: If the file set or a content digest differs.
        OSError: If a release artifact cannot be read.
    """
    manifest = ReleaseManifest.model_validate_json(
        (release_root / "manifest.json").read_text(encoding="utf-8")
    )
    actual = {path.name for path in release_root.iterdir() if path.is_file()}
    if actual != {*manifest.files, "manifest.json"}:
        raise ValueError("Release file set is not closed")
    for name, digest in manifest.files.items():
        if sha256_file(release_root / name) != digest:
            raise ValueError(f"Release hash mismatch: {name}")
    payload = {
        "release_id": manifest.release_id,
        "run_id": manifest.run_id,
        "source_run_manifest_sha256": manifest.source_run_manifest_sha256,
        "files": manifest.files,
    }
    if hashlib.sha256(canonical_json(payload)).hexdigest() != manifest.aggregate_sha256:
        raise ValueError("Release aggregate mismatch")
    return manifest
