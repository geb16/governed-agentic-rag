"""Expose the supported API for sealing and verifying evaluation releases."""

from paired_agent_evaluation.release.release_files import RELEASE_FILES
from paired_agent_evaluation.release.sealing import seal_run
from paired_agent_evaluation.release.verification import (
    verify_primary_artifacts,
    verify_release,
)

__all__ = ["RELEASE_FILES", "seal_run", "verify_primary_artifacts", "verify_release"]
