"""Admin endpoints for installation status and replay operations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import DeliveryLog, InstallationSetting, ReviewRun, get_db_session
from app.services.task_queue import InMemoryTaskQueue

router = APIRouter()


def _get_queue(request: Request) -> InMemoryTaskQueue:
    queue = getattr(request.app.state, "task_queue", None)
    if queue is None:
        raise HTTPException(status_code=500, detail="Task queue is not configured")
    return queue


@router.get("/ping")
async def admin_ping() -> dict[str, str]:
    """Basic admin router health endpoint."""
    return {"status": "admin-router-ready"}


@router.get("/installations/{installation_id}/status")
async def installation_status(
    installation_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return operational status for one installation."""
    queue = _get_queue(request)

    setting = (
        await session.execute(
            select(InstallationSetting).where(InstallationSetting.installation_id == installation_id)
        )
    ).scalars().first()

    delivery_counts = await session.execute(
        select(DeliveryLog.status, func.count())
        .where(DeliveryLog.installation_id == installation_id)
        .group_by(DeliveryLog.status)
    )
    deliveries_by_status = {status: count for status, count in delivery_counts.all()}

    run_counts = await session.execute(
        select(ReviewRun.status, func.count())
        .where(ReviewRun.installation_id == installation_id)
        .group_by(ReviewRun.status)
    )
    runs_by_status = {status: count for status, count in run_counts.all()}

    recent_runs = await session.execute(
        select(ReviewRun)
        .where(ReviewRun.installation_id == installation_id)
        .order_by(ReviewRun.created_at.desc())
        .limit(10)
    )

    queue_stats = queue.stats()
    return {
        "installation_id": installation_id,
        "feature_flags": (setting.feature_flags_json if setting else {}),
        "locale": setting.locale if setting else "en",
        "deliveries_by_status": deliveries_by_status,
        "runs_by_status": runs_by_status,
        "queue": {
            "backend": queue_stats.backend,
            "workers": queue_stats.workers,
            "pending_jobs": queue_stats.pending_jobs,
        },
        "recent_runs": [
            {
                "id": run.id,
                "run_type": run.run_type,
                "status": run.status,
                "repository": run.repository_full_name,
                "pr_number": run.pr_number,
                "created_at": run.created_at,
            }
            for run in recent_runs.scalars().all()
        ],
    }


@router.post("/installations/{installation_id}/replay/{event_id}")
async def replay_webhook_event(
    installation_id: int,
    event_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str | int]:
    """Replay an already persisted event for an installation."""
    queue = _get_queue(request)

    source_log = (
        await session.execute(
            select(DeliveryLog).where(
                DeliveryLog.webhook_event_id == event_id,
                DeliveryLog.installation_id == installation_id,
            )
        )
    ).scalars().first()

    if source_log is None:
        raise HTTPException(status_code=404, detail="Event not found for installation")

    replay_seed = f"replay:{installation_id}:{event_id}:{datetime.now(tz=timezone.utc).isoformat()}"
    replay_key = hashlib.sha256(replay_seed.encode("utf-8")).hexdigest()[:48]

    replay_log = DeliveryLog(
        platform=source_log.platform,
        delivery_id=f"replay-{event_id}",
        idempotency_key=replay_key,
        webhook_event_id=source_log.webhook_event_id,
        installation_id=installation_id,
        status="queued",
        normalized_event=source_log.normalized_event,
    )
    session.add(replay_log)
    await session.commit()
    await session.refresh(replay_log)

    await queue.enqueue("process_delivery_log", {"delivery_log_id": replay_log.id})

    return {
        "status": "queued",
        "installation_id": installation_id,
        "event_id": event_id,
        "delivery_log_id": replay_log.id,
    }
