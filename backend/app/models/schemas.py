"""Pydantic schemas placeholder for API request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema for health check endpoints."""

    status: str
    environment: str
    llm_provider: str


class WebhookEventResponse(BaseModel):
    """Response schema for accepted webhook events."""

    status: str
    event_id: int
    event_type: str
    created_at: datetime | None = None
