"""Create and verify the preregistered evaluation harness freeze.

References:
    [1] NIST, "AI Risk Management Framework Core," Measure 2.1 and 2.13.
        https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
    [2] SLSA, "Provenance."
        https://slsa.dev/spec/v1.2/provenance
"""

from __future__ import annotations

from paired_agent_evaluation.adapters.storage.filesystem import (
    atomic_json,
    directory_has_payload,
    sha256_json,
)
from paired_agent_evaluation.domain.manifests import HarnessFreezeManifest
from paired_agent_evaluation.experiment_control.contracts import EvaluationControlPaths
from paired_agent_evaluation.experiment_control.identity import (
    completed_validation,
    inherited_identities,
    manifest_payload,
    source_hashes,
)
from paired_agent_evaluation.experiment_control.policy import (
    HARNESS_FREEZE_ID,
    HARNESS_MANIFEST,
    RELEASE_PLACEHOLDERS,
    TEST_EXECUTION_CLAIM,
)
from paired_agent_evaluation.experiment_control.readiness import verify_harness_readiness


def write_harness_freeze(
    paths: EvaluationControlPaths,
    *,
    validation_run_id: str,
    test_run_id: str,
) -> HarnessFreezeManifest:
    """Freezes a validated harness and preregisters one untouched test run.

    Returns:
        The persisted, self-digested harness freeze manifest.

    Raises:
        ValueError: If prerequisites, identities, or lifecycle guards fail.
        OSError: If required evidence cannot be read or written.
    """
    if validation_run_id == test_run_id:
        raise ValueError("Validation and test runs require distinct identifiers")
    if (paths.repository / TEST_EXECUTION_CLAIM).exists():
        raise ValueError("Test execution has already been claimed; harness cannot be refrozen")
    if paths.run_root(test_run_id).exists():
        raise ValueError("Preregistered test run directory already exists")
    if directory_has_payload(paths.release, ignored_names=RELEASE_PLACEHOLDERS):
        raise ValueError("A sealed test release already exists")
    verify_harness_readiness(paths)
    validation_manifest_hash, validation_summary_hash = completed_validation(
        paths,
        validation_run_id,
    )
    manifest = HarnessFreezeManifest(
        freeze_id=HARNESS_FREEZE_ID,
        preregistered_test_run_id=test_run_id,
        validation_run_id=validation_run_id,
        validation_run_manifest_sha256=validation_manifest_hash,
        validation_summary_sha256=validation_summary_hash,
        source_files=source_hashes(paths),
        aggregate_sha256="0" * 64,
        **inherited_identities(paths),
    )
    manifest = manifest.model_copy(
        update={"aggregate_sha256": sha256_json(manifest_payload(manifest))}
    )
    atomic_json(paths.repository / HARNESS_MANIFEST, manifest.model_dump(mode="json"))
    return manifest


def verify_harness_freeze(paths: EvaluationControlPaths) -> HarnessFreezeManifest:
    """Verifies the harness manifest and every identity bound by its freeze.

    Returns:
        The validated manifest when all identities and digests match.

    Raises:
        ValueError: If the harness is absent or any frozen identity drifted.
    """
    verify_harness_readiness(paths)
    manifest_path = paths.repository / HARNESS_MANIFEST
    if not manifest_path.is_file():
        raise ValueError("Phase 6 harness is not frozen and preregistered")
    manifest = HarnessFreezeManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.freeze_id != HARNESS_FREEZE_ID:
        raise ValueError("Unexpected Phase 6 harness freeze identity")
    if manifest.source_files != source_hashes(paths):
        raise ValueError("Phase 6 harness source files changed after preregistration")
    inherited = inherited_identities(paths)
    if any(getattr(manifest, name) != value for name, value in inherited.items()):
        raise ValueError("Inherited freeze identity changed after Phase 6 preregistration")
    validation_manifest_hash, validation_summary_hash = completed_validation(
        paths,
        manifest.validation_run_id,
    )
    if (
        validation_manifest_hash != manifest.validation_run_manifest_sha256
        or validation_summary_hash != manifest.validation_summary_sha256
    ):
        raise ValueError("Validation evidence changed after Phase 6 preregistration")
    if sha256_json(manifest_payload(manifest)) != manifest.aggregate_sha256:
        raise ValueError("Phase 6 harness aggregate hash mismatch")
    return manifest
