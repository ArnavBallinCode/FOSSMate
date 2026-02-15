"""Pydantic schemas and internal contracts for orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for health check endpoints."""

    status: str
    environment: str
    llm_provider: str
    queue_backend: str
    queue_workers: int
    queue_pending_jobs: int
    database_ready: bool


class WebhookEventResponse(BaseModel):
    """Response schema for accepted webhook events."""

    status: str
    event_id: int
    event_type: str
    platform: Literal["github", "gitlab"]
    duplicate: bool = False
    created_at: datetime | None = None


class NormalizedEvent(BaseModel):
    """Platform-neutral event shape used by downstream processors."""

    platform: Literal["github", "gitlab"]
    delivery_id: str
    event_type: str
    action: str
    installation_id: int | None = None
    repository_id: int | None = None
    repository_owner: str | None = None
    repository_name: str | None = None
    repository_full_name: str | None = None
    pr_number: int | None = None
    pr_title: str | None = None
    issue_number: int | None = None
    issue_title: str | None = None
    sender_login: str | None = None
    head_sha: str | None = None
    language: Literal["en", "zh"] = "en"
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any]


class FileChangeSummary(BaseModel):
    """Summary for one changed file in a pull request."""

    path: str
    status: str = "modified"
    additions: int = 0
    deletions: int = 0
    summary: str
    risk: Literal["low", "medium", "high"] = "low"


class ReviewSuggestion(BaseModel):
    """Non-blocking code review suggestion."""

    file_path: str | None = None
    title: str
    details: str
    severity: Literal["low", "medium", "high"] = "medium"


class ScoreCard(BaseModel):
    """Advisory quality scores for pull request changes."""

    correctness: float
    readability: float
    maintainability: float
    overall: float
    advisory_only: bool = True


class ReviewResult(BaseModel):
    """Unified output from the review orchestration pipeline."""

    category: Literal["feature", "fix", "refactor", "docs", "test", "chore", "mixed"]
    pr_summary: str
    major_files: list[str] = Field(default_factory=list)
    file_summaries: list[FileChangeSummary] = Field(default_factory=list)
    suggestions: list[ReviewSuggestion] = Field(default_factory=list)
    score_card: ScoreCard
    sources: list[str] = Field(default_factory=list)
    model_used: str


class QueueJob(BaseModel):
    """Serialized queue job payload contract."""

    id: str
    name: str
    payload: dict[str, Any]
    queued_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationPayload(BaseModel):
    """Channel-agnostic notification payload."""

    subject: str
    body_text: str
    body_html: str | None = None
    recipients: list[str] = Field(default_factory=list)


class ProviderCapabilities(BaseModel):
    """Capabilities advertised by an LLM provider adapter."""

    provider: str
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_embeddings: bool = True
    supports_structured_output: bool = False
