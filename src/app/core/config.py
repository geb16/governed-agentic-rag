"""Validated environment configuration and production security invariants."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.version import APP_VERSION


class Settings(BaseSettings):
    """Load typed runtime settings from ``RAG_``-prefixed environment values."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Governed Agentic RAG Baseline"
    app_version: str = APP_VERSION
    environment: Literal["development", "test", "production"] = "development"
    execution_profile: Literal["development", "test", "experiment"] = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    api_key: SecretStr | None = None
    safety_identifier_secret: SecretStr | None = None
    allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    max_request_bytes: int = Field(default=32_768, ge=1_024, le=1_048_576)
    max_query_chars: int = Field(default=4_000, ge=100, le=20_000)

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6"
    openai_embedding_model: str = "text-embedding-3-small"
    model_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    model_max_output_tokens: int = Field(default=1_200, ge=128, le=8_192)
    max_agent_turns: int = Field(default=4, ge=1, le=8)
    max_tool_calls: int = Field(default=3, ge=0, le=8)

    knowledge_base_dir: Path = Path("data/knowledge_base")
    chunk_size_chars: int = Field(default=1_200, ge=300, le=4_000)
    chunk_overlap_chars: int = Field(default=160, ge=0, le=800)
    retrieval_top_k: int = Field(default=4, ge=1, le=10)
    retrieval_min_score: float = Field(default=0.01, ge=0.0, le=1.0)
    retrieval_backend: Literal["lexical", "qdrant"] = "lexical"
    qdrant_url: str | None = None
    qdrant_read_api_key: SecretStr | None = None
    qdrant_admin_api_key: SecretStr | None = None
    qdrant_collection: str = "phase3_enterprise_kb"
    qdrant_timeout_seconds: int = Field(default=10, ge=1, le=60)

    synthetic_database_path: Path = Path("data/runtime/synthetic-support.db")
    experiment_run_id: str | None = Field(
        default=None,
        pattern=r"^run_[a-zA-Z0-9_-]+$",
    )
    experiment_manifest_dir: Path = Path("artifacts/runs")

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: object) -> object:
        """Parse allowed hosts from a JSON array or comma-separated string.

        Args:
            value: Raw settings value supplied by Pydantic Settings.

        Returns:
            A host list for string input, otherwise the original value.

        Raises:
            ValueError: If a JSON value is valid JSON but is not an array.
        """
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                decoded = json.loads(stripped)
                if not isinstance(decoded, list):
                    raise ValueError("allowed_hosts JSON value must be an array")
                return decoded
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_security_configuration(self) -> Settings:
        """Enforce cross-field retrieval, experiment, and production constraints.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If settings would create an invalid or unsafe runtime profile.
        """
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("chunk_overlap_chars must be smaller than chunk_size_chars")
        if self.environment == "production":
            if self.api_key is None or not self.api_key.get_secret_value():
                raise ValueError("RAG_API_KEY is required in production")
            if self.openai_api_key is None or not self.openai_api_key.get_secret_value():
                raise ValueError("RAG_OPENAI_API_KEY is required in production")
            if (
                self.safety_identifier_secret is None
                or not self.safety_identifier_secret.get_secret_value()
            ):
                raise ValueError("RAG_SAFETY_IDENTIFIER_SECRET is required in production")
            if "*" in self.allowed_hosts:
                raise ValueError("Wildcard hosts are not allowed in production")
            if self.retrieval_backend == "qdrant":
                if self.qdrant_url is None or not self.qdrant_url.lower().startswith("https://"):
                    raise ValueError("Production Qdrant connections must use HTTPS")
                if self.qdrant_read_api_key is None:
                    raise ValueError("RAG_QDRANT_READ_API_KEY is required in production")
        if self.retrieval_backend == "qdrant" and not self.qdrant_url:
            raise ValueError("RAG_QDRANT_URL is required for the qdrant retrieval backend")
        if self.execution_profile == "experiment":
            if self.retrieval_backend != "qdrant":
                raise ValueError("The experiment profile requires RAG_RETRIEVAL_BACKEND=qdrant")
            if self.openai_api_key is None or not self.openai_api_key.get_secret_value():
                raise ValueError("The experiment profile requires RAG_OPENAI_API_KEY")
            if self.experiment_run_id is None:
                raise ValueError("The experiment profile requires RAG_EXPERIMENT_RUN_ID")
            if (
                self.safety_identifier_secret is None
                or not self.safety_identifier_secret.get_secret_value()
            ):
                raise ValueError("The experiment profile requires RAG_SAFETY_IDENTIFIER_SECRET")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-cached environment configuration."""
    return Settings()
