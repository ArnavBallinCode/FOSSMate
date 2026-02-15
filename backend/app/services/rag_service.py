"""RAG orchestration service."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.llm_service import LLMProvider
from app.services.vector_service import VectorService


@dataclass(slots=True)
class RAGService:
    """Retrieval + generation workflow with source references."""

    llm_provider: LLMProvider
    vector_service: VectorService

    async def answer_question(self, question: str, top_k: int = 5) -> dict[str, object]:
        """Retrieve relevant chunks and generate a grounded answer."""
        matches: list[dict[str, object]] = []
        try:
            query_embedding = await self.llm_provider.embed_text(question)
            matches = await self.vector_service.query(query_embedding, top_k=top_k)
        except Exception:
            # Keep chat endpoint resilient even when embedding provider is unavailable.
            matches = []

        contexts: list[str] = []
        sources: list[str] = []
        for item in matches:
            payload = item.get("payload", {})
            content = str(payload.get("content", ""))
            path = str(payload.get("path", ""))
            repo = str(payload.get("repo", ""))
            if content:
                contexts.append(f"[{repo}:{path}]\n{content}")
            if path:
                sources.append(f"{repo}:{path}")

        context_block = "\n\n---\n\n".join(contexts) if contexts else "No context retrieved."
        prompt = (
            "Answer the repository question using only the provided context. "
            "If context is insufficient, say so explicitly.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context_block}\n"
        )
        try:
            answer = await self.llm_provider.generate(prompt)
        except Exception:
            answer = (
                "I could not generate an LLM response right now. "
                "Please verify provider credentials or model availability."
            )

        unique_sources = list(dict.fromkeys(sources))
        return {
            "question": question,
            "answer": answer,
            "sources": unique_sources,
        }
