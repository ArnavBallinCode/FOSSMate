"""Repository ingestion service for docs/code retrieval indexing."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from app.models.schemas import NormalizedEvent
from app.services.github_service import GitHubService
from app.services.llm_service import LLMProvider
from app.services.vector_service import VectorService


@dataclass(slots=True)
class IngestionService:
    """Ingest repository docs and code chunks into vector storage."""

    github_service: GitHubService
    llm_provider: LLMProvider
    vector_service: VectorService

    async def ingest_repository(self, repo_full_name: str, installation_id: int) -> dict[str, str | int]:
        """Fetch files, chunk content, embed, and index vectors."""
        branch = await self.github_service.get_repository_default_branch(repo_full_name, installation_id)
        tree = await self.github_service.get_repository_tree(repo_full_name, installation_id, branch)

        candidate_paths: list[str] = []
        priority_paths: list[str] = []

        for item in tree:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", ""))
            lower = path.lower()

            if lower.endswith((".py", ".js", ".ts", ".md")):
                candidate_paths.append(path)
            if re.search(r"(^|/)readme", lower) or re.search(r"(^|/)contributing", lower):
                priority_paths.append(path)

        ordered_paths = list(dict.fromkeys(priority_paths + candidate_paths))

        vectors: list[list[float]] = []
        payloads: list[dict] = []
        ids: list[int] = []
        total_chunks = 0

        for path in ordered_paths[:200]:
            try:
                content = await self.github_service.get_file_content(repo_full_name, installation_id, path)
            except Exception:
                continue

            chunks = self._chunk_content(path, content)
            for index, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                embedding = await self.llm_provider.embed_text(chunk[:8000])
                vectors.append(embedding)
                payloads.append(
                    {
                        "repo": repo_full_name,
                        "path": path,
                        "chunk_index": index,
                        "content": chunk,
                        "type": self._classify_file(path),
                    }
                )
                ids.append(self._stable_id(repo_full_name, path, index))
                total_chunks += 1

        await self.vector_service.upsert_chunks(vectors=vectors, payloads=payloads, ids=ids)
        return {
            "status": "indexed",
            "repo": repo_full_name,
            "files_processed": len(ordered_paths),
            "chunks_indexed": total_chunks,
        }

    async def ingest_from_event(self, event: NormalizedEvent) -> dict[str, str | int]:
        """Convenience wrapper to ingest repository from normalized event."""
        if not event.repository_full_name or event.installation_id is None:
            return {"status": "skipped", "reason": "missing_repo_or_installation"}
        return await self.ingest_repository(event.repository_full_name, event.installation_id)

    def _chunk_content(self, path: str, content: str) -> list[str]:
        file_type = self._classify_file(path)
        if file_type == "docs":
            return self._chunk_docs(content)
        return self._chunk_code(content)

    @staticmethod
    def _chunk_docs(content: str) -> list[str]:
        sections = re.split(r"\n(?=#|##|###)\s*", content)
        if len(sections) > 1:
            return [section.strip() for section in sections if section.strip()]
        return [content[i : i + 1500] for i in range(0, len(content), 1500)]

    @staticmethod
    def _chunk_code(content: str) -> list[str]:
        # Lightweight symbol-aware split: function/class boundaries.
        blocks = re.split(r"\n(?=(def |class |export function|function |const .*?=\s*\(|async def ))", content)
        merged: list[str] = []
        buffer = ""
        for block in blocks:
            if len(buffer) + len(block) < 1800:
                buffer += block
                continue
            if buffer.strip():
                merged.append(buffer.strip())
            buffer = block
        if buffer.strip():
            merged.append(buffer.strip())
        return merged or [content[:1800]]

    @staticmethod
    def _classify_file(path: str) -> str:
        if path.lower().endswith(".md"):
            return "docs"
        return "code"

    @staticmethod
    def _stable_id(repo_full_name: str, path: str, index: int) -> int:
        digest = hashlib.sha1(f"{repo_full_name}:{path}:{index}".encode("utf-8")).hexdigest()[:15]
        return int(digest, 16)
