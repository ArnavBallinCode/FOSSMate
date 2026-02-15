"""Admin endpoints placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def admin_ping() -> dict[str, str]:
    """Basic admin router health endpoint."""
    return {"status": "admin-router-ready"}
