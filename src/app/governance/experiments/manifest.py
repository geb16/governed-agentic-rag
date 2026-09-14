"""Build and atomically record the reproducibility identity of a governed run.

The manifest binds one experiment run to the reviewed Phase 3 control, governance
and audit source, policy and schema versions, knowledge corpus, tool schemas,
provider configuration, and relevant package versions. Existing run identities are
reused only when their configuration digest matches.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pydantic import Field

from app.audit.schemas import AUDIT_SCHEMA_VERSION
from app.baseline.tool_router import ToolRouter
from app.core.config import Settings
from app.core.version import BASELINE_FREEZE_ID
from app.domain.contracts import StrictModel
from app.governance.contracts import STAGE_ORDER
from app.governance.stages.risk import GOVERNANCE_POLICY_VERSION
from app.governance.version import (
    BASELINE_CONTROL_SHA256,
    GOVERNED_APP_VERSION,
    WORKFLOW_SCHEMA_VERSION,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PHASE3_MANIFEST = _PROJECT_ROOT / "docs" / "phase-3-baseline" / "freeze-manifest.json"


def _sha256_bytes(value: bytes) -> str:
    """Return the lowercase SHA-256 digest of an exact byte sequence."""
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    """Hash a value after deterministic, whitespace-free JSON serialization."""
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def verify_phase3_control_freeze() -> str:
    """Verify the named Phase 3 manifest and every file it cryptographically pins.

    Returns:
        The reviewed aggregate digest for the Phase 3 control condition.

    Raises:
        RuntimeError: If the manifest identity, aggregate, shape, or source files differ.
        OSError: If the manifest or a declared control file cannot be read.
    """
    expected = json.loads(_PHASE3_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or expected.get("manifest_schema_version") != 1:
        raise RuntimeError("Phase 3 control manifest is invalid or unsupported")
    if expected.get("freeze_id") != BASELINE_FREEZE_ID:
        raise RuntimeError("Phase 3 control manifest has an unexpected freeze identity")
    source_files = expected.get("source_files")
    if not isinstance(source_files, dict) or not all(
        isinstance(path, str) and isinstance(digest, str) for path, digest in source_files.items()
    ):
        raise RuntimeError("Phase 3 control manifest has an invalid source-file map")
    manifest_aggregate = _canonical_sha256(source_files)
    if (
        expected.get("aggregate_sha256") != manifest_aggregate
        or manifest_aggregate != BASELINE_CONTROL_SHA256
    ):
        raise RuntimeError("Phase 3 control manifest aggregate is not the reviewed baseline")
    changed = [
        relative_path
        for relative_path, expected_hash in source_files.items()
        if not (_PROJECT_ROOT / relative_path).is_file()
        or _sha256_bytes((_PROJECT_ROOT / relative_path).read_bytes()) != expected_hash
    ]
    if changed:
        raise RuntimeError(
            "Phase 3 control freeze is invalid; changed files: " + ", ".join(changed)
        )
    return manifest_aggregate


class GovernedExperimentManifest(StrictModel):
    """Identify every controlled input that can affect a governed experiment run.

    Cryptographic digests make source, corpus, tool-schema, and aggregate
    configuration drift observable. The manifest records identity and provenance;
    it does not contain provider credentials or other runtime secrets.
    """

    manifest_schema_version: int = 1
    condition: str = "governed"
    governed_app_version: str
    run_id: str
    created_at: datetime
    baseline_freeze_id: str
    baseline_freeze_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    governance_source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    governance_policy_version: str
    workflow_stages: list[str]
    workflow_schema_version: int
    audit_schema_version: int
    model: str
    embedding_model: str
    retrieval_backend: str
    qdrant_collection: str
    knowledge_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tool_schema_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    package_versions: dict[str, str]
    configuration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def build_governed_experiment_manifest(
    settings: Settings,
    tool_router: ToolRouter,
) -> GovernedExperimentManifest:
    """Build a governed manifest after verifying the frozen control condition.

    Args:
        settings: Validated experiment settings, including the unique run identity.
        tool_router: Shared allowlisted tool router whose schemas affect treatment.

    Returns:
        An in-memory manifest containing deterministic configuration identities.

    Raises:
        ValueError: If settings do not select a named experiment run.
        RuntimeError: If the Phase 3 freeze or a package identity is invalid.
        OSError: If a pinned source or knowledge manifest cannot be read.
    """
    if settings.execution_profile != "experiment" or settings.experiment_run_id is None:
        raise ValueError("A governed manifest requires the experiment profile")
    freeze_sha = verify_phase3_control_freeze()
    governance_files = sorted(
        [
            *(_PROJECT_ROOT / "src" / "app" / "governance").rglob("*.py"),
            *(_PROJECT_ROOT / "src" / "app" / "audit").rglob("*.py"),
            _PROJECT_ROOT / "src" / "app" / "governed_main.py",
        ],
        key=lambda path: path.as_posix(),
    )
    governance_hashes = {
        path.relative_to(_PROJECT_ROOT).as_posix(): _sha256_bytes(path.read_bytes())
        for path in governance_files
    }
    knowledge_sha = _sha256_bytes((settings.knowledge_base_dir / "manifest.json").read_bytes())
    configuration = {
        "condition": "governed",
        "governed_app_version": GOVERNED_APP_VERSION,
        "baseline_freeze_id": BASELINE_FREEZE_ID,
        "baseline_freeze_sha256": freeze_sha,
        "governance_source_sha256": _canonical_sha256(governance_hashes),
        "governance_policy_version": GOVERNANCE_POLICY_VERSION,
        "workflow_stages": [stage.value for stage in STAGE_ORDER],
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "model": settings.openai_model,
        "embedding_model": settings.openai_embedding_model,
        "retrieval_backend": settings.retrieval_backend,
        "qdrant_collection": settings.qdrant_collection,
        "knowledge_manifest_sha256": knowledge_sha,
        "tool_schema_sha256": _canonical_sha256(tool_router.specs),
    }
    return GovernedExperimentManifest(
        run_id=settings.experiment_run_id,
        created_at=datetime.now(UTC),
        package_versions={
            package: version(package)
            for package in ("fastapi", "openai", "pydantic", "qdrant-client")
        },
        configuration_sha256=_canonical_sha256(configuration),
        **configuration,
    )


def record_governed_experiment_manifest(
    settings: Settings,
    tool_router: ToolRouter,
) -> tuple[GovernedExperimentManifest, Path]:
    """Create one immutable-by-convention manifest file for an experiment run.

    Creation uses exclusive file mode to prevent concurrent writers from silently
    replacing run identity. An existing manifest is returned only when its
    configuration digest matches the current build.

    Args:
        settings: Validated experiment settings and manifest output directory.
        tool_router: Shared allowlisted tool router included in configuration identity.

    Returns:
        The validated manifest and its filesystem path.

    Raises:
        RuntimeError: If the run ID already exists with configuration drift.
        ValueError: If settings do not identify an experiment run.
        OSError: If the manifest cannot be read or created.
    """
    manifest = build_governed_experiment_manifest(settings, tool_router)
    path = settings.experiment_manifest_dir / manifest.run_id / "governed-manifest.json"

    def validate_existing() -> tuple[GovernedExperimentManifest, Path]:
        """Return an existing run manifest after rejecting configuration drift."""
        existing = GovernedExperimentManifest.model_validate_json(path.read_text(encoding="utf-8"))
        if existing.configuration_sha256 != manifest.configuration_sha256:
            raise RuntimeError(f"Governed experiment run {manifest.run_id} has configuration drift")
        return existing, path

    if path.exists():
        return validate_existing()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as destination:
            destination.write(manifest.model_dump_json(indent=2))
    except FileExistsError:
        return validate_existing()
    return manifest, path
