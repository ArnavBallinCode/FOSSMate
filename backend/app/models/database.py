"""Database models and async session management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy ORM models."""


class Repository(Base):
    """Tracked repositories that installed the GitHub App."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    installation_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Installation(Base):
    """GitHub installation-specific configuration storage."""

    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_installation_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InstallationSetting(Base):
    """Runtime settings and feature flags for one installation."""

    __tablename__ = "installation_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    feature_flags_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provider_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WebhookEvent(Base):
    """Raw webhook payloads for auditability and async processing."""

    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeliveryLog(Base):
    """Delivery/idempotency log with normalized event and lifecycle status."""

    __tablename__ = "delivery_logs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_delivery_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    webhook_event_id: Mapped[int] = mapped_column(ForeignKey("webhook_events.id"), nullable=False)
    installation_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="received", nullable=False)
    normalized_event: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewRun(Base):
    """Review execution metadata per processed event."""

    __tablename__ = "review_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_log_id: Mapped[int] = mapped_column(ForeignKey("delivery_logs.id"), index=True)
    installation_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    platform: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    run_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="processing", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repository_full_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    issue_number: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    actor_login: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReviewFinding(Base):
    """Individual review suggestions/findings associated with a run."""

    __tablename__ = "review_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ScoreCardModel(Base):
    """Quality scoring artifact for one review run."""

    __tablename__ = "score_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_run_id: Mapped[int] = mapped_column(
        ForeignKey("review_runs.id"), index=True, nullable=False
    )
    correctness: Mapped[float] = mapped_column(Float, nullable=False)
    readability: Mapped[float] = mapped_column(Float, nullable=False)
    maintainability: Mapped[float] = mapped_column(Float, nullable=False)
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    advisory_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DeveloperMetric(Base):
    """Aggregated per-developer evaluation data points."""

    __tablename__ = "developer_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    installation_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    platform: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    repository_full_name: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    developer_login: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    review_run_id: Mapped[int | None] = mapped_column(ForeignKey("review_runs.id"), nullable=True)
    correctness: Mapped[float] = mapped_column(Float, nullable=False)
    readability: Mapped[float] = mapped_column(Float, nullable=False)
    maintainability: Mapped[float] = mapped_column(Float, nullable=False)
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_database(database_url: str) -> None:
    """Initialize SQLAlchemy engine/session factory for the provided URL."""
    global _engine, _session_factory

    if _engine is not None and str(_engine.url) == database_url:
        return

    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the configured async session factory."""
    if _session_factory is None:
        raise RuntimeError("Database is not configured. Call configure_database() first.")
    return _session_factory


async def init_db() -> None:
    """Create database tables if they do not exist."""
    if _engine is None:
        raise RuntimeError("Database is not configured. Call configure_database() first.")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
