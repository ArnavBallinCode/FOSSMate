"""Vector database service backed by Qdrant."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import Settings


@dataclass(slots=True)
class VectorService:
    """Qdrant vector operations used by ingestion and RAG services."""

    settings: Settings
    client: AsyncQdrantClient = field(init=False)
    collection_name: str = field(init=False)

    def __post_init__(self) -> None:
        location = ":memory:" if self.settings.is_qdrant_in_memory else None
        self.client = AsyncQdrantClient(url=None if location else self.settings.qdrant_url, location=location)
        self.collection_name = self.settings.qdrant_collection_name

    async def ensure_collection(self, vector_size: int) -> None:
        """Create collection if missing."""
        collections = await self.client.get_collections()
        existing = {item.name for item in collections.collections}
        if self.collection_name in existing:
            return

        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    async def upsert_chunks(
        self,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[int],
    ) -> None:
        """Upsert chunk embeddings with payload metadata."""
        if not vectors:
            return
        await self.ensure_collection(vector_size=len(vectors[0]))

        points = [
            PointStruct(id=ids[idx], vector=vectors[idx], payload=payloads[idx])
            for idx in range(len(vectors))
        ]
        await self.client.upsert(collection_name=self.collection_name, points=points)

    async def query(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Semantic search for top-k chunks."""
        if not vector:
            return []
        try:
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=top_k,
                with_payload=True,
            )
        except Exception:
            return []
        formatted: list[dict[str, Any]] = []
        for item in results:
            formatted.append(
                {
                    "id": item.id,
                    "score": item.score,
                    "payload": item.payload or {},
                }
            )
        return formatted

    async def health(self) -> str:
        """Return service status text."""
        return "vector-service-ready"
