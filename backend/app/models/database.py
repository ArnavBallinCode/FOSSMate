"""Database models and async session management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, func
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
