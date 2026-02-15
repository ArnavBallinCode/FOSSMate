"""Chat endpoints placeholder."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.services.llm_service import get_llm_provider
from app.services.rag_service import RAGService
from app.services.vector_service import VectorService

router = APIRouter()


@router.get("/ping")
async def chat_ping() -> dict[str, str]:
    """Basic chat router health endpoint."""
    return {"status": "chat-router-ready"}


class ChatRequest(BaseModel):
    """Chat query payload for repository-aware Q&A."""

    question: str = Field(min_length=3, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/ask")
async def ask_question(
    body: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Answer a repository question using RAG retrieval."""
    llm_provider = get_llm_provider()
    vector_service = VectorService(settings=settings)
    rag = RAGService(llm_provider=llm_provider, vector_service=vector_service)
    return await rag.answer_question(question=body.question, top_k=body.top_k)
