"""Expose governed experiment identity construction and freeze verification.

The public surface records a reproducible treatment manifest while verifying that
the Phase 3 control remains byte-for-byte identical to its reviewed freeze.
"""

from app.governance.experiments.manifest import (
    GovernedExperimentManifest,
    build_governed_experiment_manifest,
    record_governed_experiment_manifest,
    verify_phase3_control_freeze,
)

__all__ = [
    "GovernedExperimentManifest",
    "build_governed_experiment_manifest",
    "record_governed_experiment_manifest",
    "verify_phase3_control_freeze",
]
