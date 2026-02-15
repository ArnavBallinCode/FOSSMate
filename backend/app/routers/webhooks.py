"""GitHub/GitLab webhook receiver routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.database import DeliveryLog, WebhookEvent, get_db_session
from app.models.schemas import NormalizedEvent, WebhookEventResponse
from app.services.event_normalizer import normalize_github_event, normalize_gitlab_event
from app.services.task_queue import InMemoryTaskQueue

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_github_signature(payload: bytes, signature: str | None, webhook_secret: str) -> None:
    """Validate GitHub's `X-Hub-Signature-256` header."""
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header.",
        )

    digest = hmac.new(webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )


def verify_gitlab_token(
    token: str | None,
    expected_token: str | None,
) -> None:
    """Validate GitLab secret token when configured."""
    if not expected_token:
        return
    if not token or not hmac.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitLab webhook token.",
        )


def _idempotency_key(
    platform: str,
    delivery_id: str,
    event_type: str,
    action: str,
) -> str:
    return f"{platform}:{delivery_id}:{event_type}:{action}"


def _payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:20]


async def _persist_and_enqueue(
    platform: str,
    event_type: str,
    normalized: NormalizedEvent,
    payload: dict[str, Any],
    delivery_id: str,
    session: AsyncSession,
    queue: InMemoryTaskQueue,
) -> WebhookEventResponse:
    idempotency_key = _idempotency_key(platform, delivery_id, event_type, normalized.action)
    existing = (
        await session.execute(select(DeliveryLog).where(DeliveryLog.idempotency_key == idempotency_key))
    ).scalars().first()
    if existing:
        return WebhookEventResponse(
            status="accepted",
            event_id=existing.webhook_event_id,
            event_type=event_type,
            platform=platform,
            duplicate=True,
        )

    webhook_event = WebhookEvent(event_type=event_type, payload=payload)
    session.add(webhook_event)
    await session.commit()
    await session.refresh(webhook_event)

    delivery = DeliveryLog(
        platform=platform,
        delivery_id=delivery_id,
        idempotency_key=idempotency_key,
        webhook_event_id=webhook_event.id,
        installation_id=normalized.installation_id,
        status="queued",
        normalized_event=normalized.model_dump(mode="json"),
    )
    session.add(delivery)
    await session.commit()
    await session.refresh(delivery)

    await queue.enqueue(
        name="process_delivery_log",
        payload={"delivery_log_id": delivery.id},
    )

    logger.info(
        "Accepted %s webhook delivery=%s event=%s webhook_event_id=%s delivery_log_id=%s",
        platform,
        delivery_id,
        event_type,
        webhook_event.id,
        delivery.id,
    )

    return WebhookEventResponse(
        status="accepted",
        event_id=webhook_event.id,
        event_type=event_type,
        platform=platform,
        duplicate=False,
    )


def _get_queue(request: Request) -> InMemoryTaskQueue:
    queue = getattr(request.app.state, "task_queue", None)
    if queue is None:
        raise HTTPException(status_code=500, detail="Task queue is not configured")
    return queue


@router.post("/github", status_code=status.HTTP_202_ACCEPTED, response_model=WebhookEventResponse)
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
    x_github_event: str = Header(default="unknown", alias="X-GitHub-Event"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> WebhookEventResponse:
    """Receive GitHub webhook events, enforce idempotency, and enqueue processing."""
    raw_payload = await request.body()
    verify_github_signature(raw_payload, x_hub_signature_256, settings.github_webhook_secret)

    try:
        payload = json.loads(raw_payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    delivery_id = x_github_delivery or _payload_hash(raw_payload)
    normalized = normalize_github_event(
        event_type=x_github_event,
        delivery_id=delivery_id,
        payload=payload,
    )
    queue = _get_queue(request)

    return await _persist_and_enqueue(
        platform="github",
        event_type=x_github_event,
        normalized=normalized,
        payload=payload,
        delivery_id=delivery_id,
        session=session,
        queue=queue,
    )


@router.post("/gitlab", status_code=status.HTTP_202_ACCEPTED, response_model=WebhookEventResponse)
async def gitlab_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
    x_gitlab_event: str = Header(default="unknown", alias="X-Gitlab-Event"),
    x_gitlab_token: str | None = Header(default=None, alias="X-Gitlab-Token"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> WebhookEventResponse:
    """Receive GitLab webhook events and enqueue normalized processing."""
    if not settings.feature_gitlab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitLab webhook endpoint is disabled for this deployment.",
        )

    raw_payload = await request.body()
    verify_gitlab_token(x_gitlab_token, settings.gitlab_webhook_secret)

    try:
        payload = json.loads(raw_payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    delivery_id = x_request_id or _payload_hash(raw_payload)
    normalized = normalize_gitlab_event(
        event_type=x_gitlab_event,
        delivery_id=delivery_id,
        payload=payload,
    )
    queue = _get_queue(request)

    return await _persist_and_enqueue(
        platform="gitlab",
        event_type=x_gitlab_event,
        normalized=normalized,
        payload=payload,
        delivery_id=delivery_id,
        session=session,
        queue=queue,
    )


@router.post("/github/test")
async def github_webhook_test(payload: dict[str, Any]) -> dict[str, Any]:
    """Local testing endpoint for printing webhook payloads without signature checks."""
    logger.info("Webhook test payload: %s", payload)
    return {"received": True, "keys": sorted(payload.keys())}
