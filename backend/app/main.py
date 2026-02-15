"""FastAPI entry point for the FOSSMate backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.models.database import configure_database, get_session_factory, init_db
from app.routers.admin import router as admin_router
from app.routers.chat import router as chat_router
from app.routers.reports import router as reports_router
from app.routers.webhooks import router as webhook_router
from app.services.github_service import GitHubService
from app.services.llm_service import get_llm_provider
from app.services.notification_service import NotificationService
from app.services.review_service import ReviewService
from app.services.task_queue import InMemoryTaskQueue
from app.services.webhook_processor import WebhookProcessor
from app.utils.github_auth import GitHubAppAuth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources before serving requests."""
    settings = get_settings()
    configure_database(settings.database_url)
    await init_db()

    queue = InMemoryTaskQueue(workers=settings.queue_workers)
    auth = GitHubAppAuth(settings)
    github_service = GitHubService(settings=settings, auth=auth)
    llm_provider = get_llm_provider()
    review_service = ReviewService(llm_provider=llm_provider, github_service=github_service)
    notification_service = NotificationService(settings=settings)
    processor = WebhookProcessor(
        settings=settings,
        session_factory=get_session_factory(),
        github_service=github_service,
        review_service=review_service,
        notification_service=notification_service,
    )
    queue.register_handler("process_delivery_log", processor.process_delivery_log)
    await queue.start()

    app.state.task_queue = queue
    app.state.github_service = github_service
    app.state.review_service = review_service
    app.state.webhook_processor = processor

    logger.info("FOSSMate API started with provider=%s", settings.llm_provider)
    yield
    await queue.stop()
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
app.include_router(reports_router, prefix="/reports", tags=["reports"])


@app.get("/health", summary="Health check")
async def health_check(settings: Settings = Depends(get_settings)) -> dict[str, str | int | bool]:
    """Return service health and current LLM provider."""
    queue = getattr(app.state, "task_queue", None)
    queue_stats = queue.stats() if queue else None

    db_ready = True
    try:
        get_session_factory()
    except (RuntimeError, SQLAlchemyError):
        db_ready = False

    return {
        "status": "ok",
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "queue_backend": queue_stats.backend if queue_stats else "uninitialized",
        "queue_workers": queue_stats.workers if queue_stats else 0,
        "queue_pending_jobs": queue_stats.pending_jobs if queue_stats else 0,
        "database_ready": db_ready,
    }
