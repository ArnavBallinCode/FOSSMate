"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for GitHub, LLM, and storage services."""

    _PROJECT_ROOT = Path(__file__).resolve().parents[2]

    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env", _PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = Field(
        default="development", validation_alias="APP_ENV"
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    github_app_id: str = Field(default="", validation_alias="GITHUB_APP_ID")
    github_private_key: str = Field(default="", validation_alias="GITHUB_PRIVATE_KEY")
    github_webhook_secret: str = Field(default="", validation_alias="GITHUB_WEBHOOK_SECRET")
    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    ngrok_authtoken: str | None = Field(default=None, validation_alias="NGROK_AUTHTOKEN")

    llm_provider: Literal["gemini", "openai", "ollama", "custom"] = Field(
        default="gemini", validation_alias="LLM_PROVIDER"
    )
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_name: str = Field(default="gemini-2.0-flash", validation_alias="LLM_MODEL_NAME")
    llm_embedding_model: str = Field(
        default="models/text-embedding-004", validation_alias="LLM_EMBEDDING_MODEL"
    )
    llm_endpoint: str | None = Field(default=None, validation_alias="LLM_ENDPOINT")

    qdrant_url: str = Field(default="in-memory", validation_alias="QDRANT_URL")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./fossmate.db", validation_alias="DATABASE_URL"
    )

    @field_validator("github_app_id", "github_private_key", "github_webhook_secret", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: str | None) -> str:
        if value is None:
            return ""
        return value.strip()

    @field_validator("llm_api_key", "llm_endpoint", mode="before")
    @classmethod
    def _normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_required_config(self) -> "Settings":
        missing_github = [
            key
            for key, value in {
                "GITHUB_APP_ID": self.github_app_id,
                "GITHUB_PRIVATE_KEY": self.github_private_key,
                "GITHUB_WEBHOOK_SECRET": self.github_webhook_secret,
            }.items()
            if not value
        ]
        if missing_github:
            joined = ", ".join(missing_github)
            raise ValueError(f"Missing required GitHub settings: {joined}")

        if self.llm_provider in {"gemini", "openai", "custom"} and not self.llm_api_key:
            raise ValueError(
                f"LLM_API_KEY is required when LLM_PROVIDER is '{self.llm_provider}'."
            )

        if self.llm_provider == "custom" and not self.llm_endpoint:
            raise ValueError("LLM_ENDPOINT is required when LLM_PROVIDER is 'custom'.")

        if self.llm_provider == "ollama" and not self.llm_endpoint:
            self.llm_endpoint = "http://localhost:11434"

        return self

    @property
    def github_private_key_pem(self) -> str:
        """Return PEM key with escaped newlines normalized for JWT signing."""
        return self.github_private_key.replace("\\n", "\n")

    @property
    def is_qdrant_in_memory(self) -> bool:
        """Whether the app should use in-memory vector storage."""
        return self.qdrant_url.lower() in {"in-memory", "memory", ":memory:"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache validated settings for dependency injection."""
    return Settings()
