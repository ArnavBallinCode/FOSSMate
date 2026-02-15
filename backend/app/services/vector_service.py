"""Vector database service placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class VectorService:
    """Stub vector service for future Qdrant integration."""

    async def health(self) -> str:
        """Placeholder vector service status method."""
        return "vector-service-ready"
