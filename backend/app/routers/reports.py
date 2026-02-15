"""Reporting endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import DeveloperMetric, get_db_session

router = APIRouter()


@router.get("/developer-evaluation")
async def developer_evaluation(
    installation_id: int | None = Query(default=None),
    developer_login: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Return aggregated developer quality metrics over a time window."""
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    filters = [DeveloperMetric.measured_at >= since]
    if installation_id is not None:
        filters.append(DeveloperMetric.installation_id == installation_id)
    if developer_login:
        filters.append(DeveloperMetric.developer_login == developer_login)

    query = (
        select(
            DeveloperMetric.developer_login,
            func.count(DeveloperMetric.id),
            func.avg(DeveloperMetric.correctness),
            func.avg(DeveloperMetric.readability),
            func.avg(DeveloperMetric.maintainability),
            func.avg(DeveloperMetric.overall),
        )
        .where(and_(*filters))
        .group_by(DeveloperMetric.developer_login)
        .order_by(func.avg(DeveloperMetric.overall).desc())
    )

    rows = (await session.execute(query)).all()

    return {
        "days": days,
        "installation_id": installation_id,
        "developer_login": developer_login,
        "results": [
            {
                "developer_login": row[0],
                "review_count": row[1],
                "avg_correctness": round(float(row[2] or 0), 2),
                "avg_readability": round(float(row[3] or 0), 2),
                "avg_maintainability": round(float(row[4] or 0), 2),
                "avg_overall": round(float(row[5] or 0), 2),
            }
            for row in rows
        ],
    }
