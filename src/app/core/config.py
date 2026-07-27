from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    log_level: str = "INFO"

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6"
    openai_embedding_model: str = "text-embedding-3-small"
    model_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)
    model_max_retries: int = Field(default=2, ge=0, le=5)
    model_max_output_tokens: int = Field(default=1_200, ge=128, le=8_192)
    max_agent_turns: int = Field(default=4, ge=1, le=8)
