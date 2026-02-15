"""Queue boundary abstraction with an in-memory backend implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
import logging
import uuid

from app.models.schemas import QueueJob

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict], Awaitable[None]]


@dataclass(slots=True)
class QueueStats:
    """Runtime queue status values."""

    backend: str
    workers: int
    pending_jobs: int


class InMemoryTaskQueue:
    """Simple in-memory queue with pluggable job handlers."""

    def __init__(self, workers: int = 1) -> None:
        self._workers = max(1, workers)
        self._queue: asyncio.Queue[QueueJob] = asyncio.Queue()
        self._handlers: dict[str, JobHandler] = {}
        self._worker_tasks: list[asyncio.Task[None]] = []
        self._running = False

    def register_handler(self, name: str, handler: JobHandler) -> None:
        """Register a handler for a named queue job."""
        self._handlers[name] = handler

    async def start(self) -> None:
        """Start queue worker tasks."""
        if self._running:
            return

        self._running = True
        for idx in range(self._workers):
            task = asyncio.create_task(self._worker_loop(idx), name=f"fossmate-queue-worker-{idx}")
            self._worker_tasks.append(task)

    async def stop(self) -> None:
        """Stop workers gracefully."""
        self._running = False
        for task in self._worker_tasks:
            task.cancel()
        for task in self._worker_tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._worker_tasks.clear()

    async def enqueue(self, name: str, payload: dict) -> str:
        """Enqueue a job for async processing."""
        job = QueueJob(id=str(uuid.uuid4()), name=name, payload=payload)
        await self._queue.put(job)
        return job.id

    def stats(self) -> QueueStats:
        """Return current queue runtime stats."""
        return QueueStats(
            backend="in_memory",
            workers=self._workers,
            pending_jobs=self._queue.qsize(),
        )

    async def _worker_loop(self, worker_index: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                handler = self._handlers.get(job.name)
                if handler is None:
                    logger.error("No handler registered for queue job '%s'", job.name)
                    continue
                await handler(job.payload)
            except Exception:  # pragma: no cover - defensive runtime safety
                logger.exception(
                    "Queue worker %s failed processing job name=%s id=%s",
                    worker_index,
                    job.name,
                    job.id,
                )
            finally:
                self._queue.task_done()
