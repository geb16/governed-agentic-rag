"""Shared validation base for strict cross-boundary contracts."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Base contract that strips strings and rejects undeclared fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
