"""Chat endpoints placeholder."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def chat_ping() -> dict[str, str]:
    """Basic chat router health endpoint."""
    return {"status": "chat-router-ready"}
