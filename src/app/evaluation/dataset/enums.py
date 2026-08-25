# Stable serialized vocabulary for the Phase 5 evaluation dataset.

from enum import StrEnum


class DatasetSplit(StrEnum):
    """Separate rubric validation from the final comparative test set."""

    VALIDATION = "validation"
    TEST = "test"


class ScenarioCategory(StrEnum):
    """Primary mutually exclusive benchmark stratum."""

    NORMAL = "normal"
    AMBIGUOUS = "ambiguous"
    POLICY_SENSITIVE = "policy_sensitive"
    HIGH_RISK = "high_risk"
    MISSING_INFORMATION = "missing_information"
    TOOL_FAILURE = "tool_failure"


class InteractionChannel(StrEnum):
    """Synthetic enterprise request channel."""

    CHAT = "chat"
    EMAIL = "email"
    PORTAL = "portal"
    API = "api"
