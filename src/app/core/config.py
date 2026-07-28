from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.version import APP_VERSION


class Settings(BaseSettings):
    """Environment-backed configuration"""

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
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                decoded = json.loads(stripped)
                if not isinstance(decoded, list):
                    raise ValueError("allowed_hosts JSON value must be an array")
                return decoded
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
