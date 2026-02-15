"""GitHub webhook receiver routes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.database import WebhookEvent, get_db_session, get_session_factory

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


async def process_webhook_event(event_id: int, event_type: str, payload: dict[str, Any]) -> None:
    """Background processing stub for long-running webhook workflows."""
    action = payload.get("action", "")
    logger.info("Processing webhook event id=%s type=%s action=%s", event_id, event_type, action)

    if event_type == "issues" and action == "opened":
        issue_title = payload.get("issue", {}).get("title", "")
        logger.info("TODO: summarize issue and suggest labels for '%s'", issue_title)

    elif event_type == "issue_comment" and action == "created":
        comment_body = payload.get("comment", {}).get("body", "")
        if "can i work on this" in comment_body.lower():
            logger.info("TODO: respond with contributor onboarding guidance")

    elif event_type == "pull_request" and action == "opened":
        pr_title = payload.get("pull_request", {}).get("title", "")
        logger.info("TODO: summarize newly opened PR '%s'", pr_title)

    session_factory = get_session_factory()
    async with session_factory() as session:
        event = await session.get(WebhookEvent, event_id)
        if event is not None:
            event.processed_at = datetime.now(tz=timezone.utc)
            await session.commit()


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
    x_github_event: str = Header(default="unknown", alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """Receive and persist GitHub webhook events for asynchronous processing."""
    raw_payload = await request.body()
    verify_github_signature(raw_payload, x_hub_signature_256, settings.github_webhook_secret)

    try:
        payload = json.loads(raw_payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    webhook_event = WebhookEvent(event_type=x_github_event, payload=payload)
    session.add(webhook_event)
    await session.commit()
    await session.refresh(webhook_event)

    background_tasks.add_task(process_webhook_event, webhook_event.id, x_github_event, payload)

    logger.info(
        "Accepted GitHub webhook delivery=%s event=%s db_id=%s",
        request.headers.get("X-GitHub-Delivery"),
        x_github_event,
        webhook_event.id,
    )

    return {
        "status": "accepted",
        "event_id": webhook_event.id,
        "event_type": x_github_event,
    }


@router.post("/github/test")
async def github_webhook_test(payload: dict[str, Any]) -> dict[str, Any]:
    """Local testing endpoint for printing webhook payloads without signature checks."""
    logger.info("Webhook test payload: %s", payload)
    return {"received": True, "keys": sorted(payload.keys())}
