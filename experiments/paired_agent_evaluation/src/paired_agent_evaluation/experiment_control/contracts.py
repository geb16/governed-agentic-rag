"""Define the path contract required by experiment controls."""

from pathlib import Path
from typing import Protocol


class EvaluationControlPaths(Protocol):
    """Exposes only paths required by the experiment-control boundary."""

    @property
    def repository(self) -> Path: ...

    @property
    def project(self) -> Path: ...

    @property
    def artifacts(self) -> Path: ...

    @property
    def releases(self) -> Path: ...

    @property
    def harnesses(self) -> Path: ...

    @property
    def configs(self) -> Path: ...

    def run_root(self, run_id: str) -> Path: ...

    def release_root(self, version: str) -> Path: ...

    def harness_manifest(self, harness_version: int) -> Path: ...

    def test_claim(self, harness_version: int) -> Path: ...
