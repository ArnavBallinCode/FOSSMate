"""RAG orchestration service placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RAGService:
    """Stub RAG service; retrieval + generation will be added later."""

    async def answer_question(self, question: str) -> dict[str, str]:
        """Placeholder question-answering method."""
        return {"answer": "Not implemented yet", "question": question}
