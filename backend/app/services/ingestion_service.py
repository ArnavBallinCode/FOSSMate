"""Repository ingestion service placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IngestionService:
    """Stub ingestion service; implementation follows in later iterations."""

    async def ingest_repository(self, repo_full_name: str) -> dict[str, str]:
        """Placeholder ingestion entrypoint."""
        return {"status": "pending", "repo": repo_full_name}
