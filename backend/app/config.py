"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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
    github_private_key_path: str | None = Field(default=None, validation_alias="GITHUB_PRIVATE_KEY_PATH")
    github_webhook_secret: str = Field(default="", validation_alias="GITHUB_WEBHOOK_SECRET")
    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    ngrok_authtoken: str | None = Field(default=None, validation_alias="NGROK_AUTHTOKEN")
    gitlab_webhook_secret: str | None = Field(default=None, validation_alias="GITLAB_WEBHOOK_SECRET")

    llm_provider: Literal[
        "gemini",
        "openai",
        "openrouter",
        "ollama",
        "custom",
        "azure_openai",
        "deepseek",
        "deepseek_r1",
    ] = Field(
        default="ollama", validation_alias="LLM_PROVIDER"
    )
    llm_api_key: str | None = Field(default=None, validation_alias="LLM_API_KEY")
    llm_model_name: str = Field(default="llama3.1", validation_alias="LLM_MODEL_NAME")
    llm_embedding_model: str = Field(
        default="models/text-embedding-004", validation_alias="LLM_EMBEDDING_MODEL"
    )
    llm_endpoint: str | None = Field(default=None, validation_alias="LLM_ENDPOINT")
    llm_fallback_provider: Literal[
        "none",
        "gemini",
        "openai",
        "openrouter",
        "ollama",
        "custom",
        "azure_openai",
        "deepseek",
        "deepseek_r1",
    ] = Field(default="none", validation_alias="LLM_FALLBACK_PROVIDER")
    llm_fallback_api_key: str | None = Field(default=None, validation_alias="LLM_FALLBACK_API_KEY")
    llm_fallback_model_name: str | None = Field(
        default=None, validation_alias="LLM_FALLBACK_MODEL_NAME"
    )
    llm_fallback_endpoint: str | None = Field(default=None, validation_alias="LLM_FALLBACK_ENDPOINT")
    azure_openai_api_version: str = Field(
        default="2024-10-21", validation_alias="AZURE_OPENAI_API_VERSION"
    )
    deepseek_endpoint: str = Field(
        default="https://api.deepseek.com/v1", validation_alias="DEEPSEEK_ENDPOINT"
    )
    openrouter_endpoint: str = Field(
        default="https://openrouter.ai/api/v1", validation_alias="OPENROUTER_ENDPOINT"
    )
    openrouter_site_url: str | None = Field(default=None, validation_alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str | None = Field(default=None, validation_alias="OPENROUTER_APP_NAME")

    qdrant_url: str = Field(default="in-memory", validation_alias="QDRANT_URL")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./fossmate.db", validation_alias="DATABASE_URL"
    )
    qdrant_collection_name: str = Field(
        default="fossmate_chunks", validation_alias="QDRANT_COLLECTION_NAME"
    )
    queue_workers: int = Field(default=1, validation_alias="QUEUE_WORKERS")

    feature_pr_summary: bool = Field(default=True, validation_alias="FEATURE_PR_SUMMARY")
    feature_file_summary: bool = Field(default=True, validation_alias="FEATURE_FILE_SUMMARY")
    feature_review_suggestions: bool = Field(
        default=True, validation_alias="FEATURE_REVIEW_SUGGESTIONS"
    )
    feature_scoring: bool = Field(default=True, validation_alias="FEATURE_SCORING")
    feature_commit_trigger: bool = Field(default=True, validation_alias="FEATURE_COMMIT_TRIGGER")
    feature_email_reports: bool = Field(default=False, validation_alias="FEATURE_EMAIL_REPORTS")
    feature_developer_eval: bool = Field(default=False, validation_alias="FEATURE_DEVELOPER_EVAL")
    feature_gitlab: bool = Field(default=False, validation_alias="FEATURE_GITLAB")
    feature_comment_auto_reply: bool = Field(
        default=True, validation_alias="FEATURE_COMMENT_AUTO_REPLY"
    )
    feature_comment_reply_all: bool = Field(
        default=True, validation_alias="FEATURE_COMMENT_REPLY_ALL"
    )
    assistant_handle: str = Field(default="fossmate", validation_alias="ASSISTANT_HANDLE")

    email_enabled: bool = Field(default=False, validation_alias="EMAIL_ENABLED")
    email_from: str | None = Field(default=None, validation_alias="EMAIL_FROM")
    email_smtp_host: str | None = Field(default=None, validation_alias="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, validation_alias="EMAIL_SMTP_PORT")
    email_smtp_username: str | None = Field(default=None, validation_alias="EMAIL_SMTP_USERNAME")
    email_smtp_password: str | None = Field(default=None, validation_alias="EMAIL_SMTP_PASSWORD")
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    auto_gemini_fallback: bool = Field(default=True, validation_alias="AUTO_GEMINI_FALLBACK")
    gemini_fallback_model: str = Field(
        default="gemini-2.0-flash", validation_alias="GEMINI_FALLBACK_MODEL"
    )

    @field_validator("github_app_id", "github_private_key", "github_webhook_secret", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: str | None) -> str:
        if value is None:
            return ""
        return value.strip()

    @field_validator(
        "llm_api_key",
        "llm_endpoint",
        "llm_fallback_api_key",
        "llm_fallback_model_name",
        "llm_fallback_endpoint",
        "email_from",
        "email_smtp_host",
        "email_smtp_username",
        "email_smtp_password",
        "gitlab_webhook_secret",
        "openrouter_site_url",
        "openrouter_app_name",
        "github_private_key_path",
        "assistant_handle",
        "gemini_api_key",
        mode="before",
    )
    @classmethod
    def _normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_required_config(self) -> "Settings":
        if self.llm_provider == "gemini" and not self.llm_api_key and self.gemini_api_key:
            self.llm_api_key = self.gemini_api_key

        missing_github = [
            key
            for key, value in {
                "GITHUB_APP_ID": self.github_app_id,
                "GITHUB_WEBHOOK_SECRET": self.github_webhook_secret,
            }.items()
            if not value
        ]
        if not self.github_private_key and not self.github_private_key_path:
            missing_github.append("GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH")
        if missing_github:
            joined = ", ".join(missing_github)
            raise ValueError(f"Missing required GitHub settings: {joined}")

        if self.llm_provider in {
            "gemini",
            "openai",
            "openrouter",
            "custom",
            "azure_openai",
            "deepseek",
            "deepseek_r1",
        } and not self.llm_api_key:
            raise ValueError(
                f"LLM_API_KEY is required when LLM_PROVIDER is '{self.llm_provider}'."
            )

        if self.llm_provider in {"custom", "azure_openai"} and not self.llm_endpoint:
            raise ValueError(
                "LLM_ENDPOINT is required when LLM_PROVIDER is 'custom' or 'azure_openai'."
            )

        if self.llm_provider == "ollama" and not self.llm_endpoint:
            self.llm_endpoint = "http://localhost:11434"

        if self.llm_provider in {"deepseek", "deepseek_r1"} and not self.llm_endpoint:
            self.llm_endpoint = self.deepseek_endpoint
        if self.llm_provider == "openrouter" and not self.llm_endpoint:
            self.llm_endpoint = self.openrouter_endpoint

        if self.email_enabled:
            if not self.email_from or not self.email_smtp_host:
                raise ValueError(
                    "EMAIL_FROM and EMAIL_SMTP_HOST are required when EMAIL_ENABLED=true."
                )

        return self

    @property
    def github_private_key_pem(self) -> str:
        """Return PEM key with escaped newlines normalized for JWT signing."""
        if self.github_private_key_path:
            path = Path(self.github_private_key_path).expanduser()
            if not path.exists():
                raise ValueError(f"GITHUB_PRIVATE_KEY_PATH does not exist: {path}")
            return path.read_text(encoding="utf-8")
        return self.github_private_key.replace("\\n", "\n")

    @property
    def is_qdrant_in_memory(self) -> bool:
        """Whether the app should use in-memory vector storage."""
        return self.qdrant_url.lower() in {"in-memory", "memory", ":memory:"}

    @property
    def default_feature_flags(self) -> dict[str, bool]:
        """Default feature flag values for new installations."""
        return {
            "pr_summary": self.feature_pr_summary,
            "file_summary": self.feature_file_summary,
            "review_suggestions": self.feature_review_suggestions,
            "scoring": self.feature_scoring,
            "commit_trigger": self.feature_commit_trigger,
            "email_reports": self.feature_email_reports,
            "developer_eval": self.feature_developer_eval,
            "comment_auto_reply": self.feature_comment_auto_reply,
            "comment_reply_all": self.feature_comment_reply_all,
        }

    @property
    def fallback_llm_config(self) -> dict[str, Any] | None:
        """Return fallback provider config when enabled."""
        if self.llm_fallback_provider == "none":
            inferred_gemini_key = self.gemini_api_key
            if not inferred_gemini_key and self.llm_provider == "ollama":
                inferred_gemini_key = self.llm_api_key
            if self.auto_gemini_fallback and self.llm_provider != "gemini" and inferred_gemini_key:
                return {
                    "provider": "gemini",
                    "api_key": inferred_gemini_key,
                    "model_name": self.gemini_fallback_model,
                    "endpoint": None,
                }
            return None
        return {
            "provider": self.llm_fallback_provider,
            "api_key": self.llm_fallback_api_key or self.llm_api_key,
            "model_name": self.llm_fallback_model_name or self.llm_model_name,
            "endpoint": self.llm_fallback_endpoint or self.llm_endpoint,
        }

    @property
    def openrouter_headers(self) -> dict[str, str]:
        """Optional headers recommended by OpenRouter."""
        headers: dict[str, str] = {}
        if self.openrouter_site_url:
            headers["HTTP-Referer"] = self.openrouter_site_url
        if self.openrouter_app_name:
            headers["X-Title"] = self.openrouter_app_name
        return headers


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache validated settings for dependency injection."""
    return Settings()
