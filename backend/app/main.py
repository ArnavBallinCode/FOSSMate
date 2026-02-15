"""FastAPI entry point for the FOSSMate backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.models.database import configure_database, init_db
from app.routers.admin import router as admin_router
from app.routers.chat import router as chat_router
from app.routers.webhooks import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize shared resources before serving requests."""
    settings = get_settings()
    configure_database(settings.database_url)
    await init_db()
    logger.info("FOSSMate API started with provider=%s", settings.llm_provider)
    yield
    logger.info("FOSSMate API shutdown complete")


app = FastAPI(
    title="FOSSMate Backend",
    description="AI maintainer assistant for open-source repositories",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.get("/health", summary="Health check")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Return service health and current LLM provider."""
    return {
        "status": "ok",
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
    }
