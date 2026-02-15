"""LLM provider abstraction and concrete provider implementations."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import lru_cache
import json
import threading
from typing import Any, AsyncIterator

import google.generativeai as genai
import httpx
from openai import AsyncOpenAI

from app.config import Settings, get_settings


class LLMProvider(ABC):
    """Base interface for all LLM providers used by the application."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate a full completion for the given prompt."""

    @abstractmethod
    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        """Generate a streamed completion token-by-token."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Create an embedding for retrieval workflows."""


class GeminiProvider(LLMProvider):
    """Google Gemini provider using the `google-generativeai` client."""

    def __init__(self, api_key: str, model_name: str, embedding_model: str) -> None:
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name=model_name)
        self._embedding_model = embedding_model

    @staticmethod
    def _build_prompt(prompt: str, system_prompt: str | None = None) -> str:
        if not system_prompt:
            return prompt
        return f"System instructions:\n{system_prompt}\n\nUser request:\n{prompt}"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        full_prompt = self._build_prompt(prompt, system_prompt)

        def _sync_generate() -> str:
            response = self._model.generate_content(full_prompt)
            return getattr(response, "text", "") or ""

        return await asyncio.to_thread(_sync_generate)

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        full_prompt = self._build_prompt(prompt, system_prompt)
        queue: asyncio.Queue[str | Exception | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _worker() -> None:
            try:
                stream = self._model.generate_content(full_prompt, stream=True)
                for chunk in stream:
                    text = getattr(chunk, "text", "")
                    if text:
                        loop.call_soon_threadsafe(queue.put_nowait, text)
            except Exception as exc:  # pragma: no cover - defensive runtime safety
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    async def embed_text(self, text: str) -> list[float]:
        def _sync_embed() -> list[float]:
            result = genai.embed_content(
                model=self._embedding_model,
                content=text,
                task_type="retrieval_document",
            )
            embedding = result.get("embedding") if isinstance(result, dict) else None
            if not embedding:
                raise ValueError("Gemini embedding response did not include an embedding vector.")
            return [float(value) for value in embedding]

        return await asyncio.to_thread(_sync_embed)


class OpenAIProvider(LLMProvider):
    """OpenAI provider for OpenAI-hosted models."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model_name
        self._embedding_model = embedding_model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def embed_text(self, text: str) -> list[float]:
        result = await self._client.embeddings.create(model=self._embedding_model, input=text)
        return [float(value) for value in result.data[0].embedding]


class OllamaProvider(LLMProvider):
    """Ollama provider using Ollama's local HTTP API."""

    def __init__(self, endpoint: str, model_name: str) -> None:
        self._client = httpx.AsyncClient(base_url=endpoint.rstrip("/"), timeout=120.0)
        self._model_name = model_name

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await self._client.post("/api/generate", json=payload)
        response.raise_for_status()
        return response.json().get("response", "")

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self._model_name,
            "prompt": prompt,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with self._client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                item = json.loads(line)
                token = item.get("response", "")
                if token:
                    yield token

    async def embed_text(self, text: str) -> list[float]:
        response = await self._client.post(
            "/api/embeddings",
            json={"model": self._model_name, "prompt": text},
        )
        response.raise_for_status()
        vector = response.json().get("embedding")
        if not isinstance(vector, list):
            raise ValueError("Ollama embeddings response did not include an embedding vector.")
        return [float(value) for value in vector]


class CustomProvider(OpenAIProvider):
    """OpenAI-compatible provider for custom/self-hosted endpoints."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model_name: str,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=endpoint,
            embedding_model=embedding_model,
        )


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Select an LLM provider implementation from app settings."""
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            api_key=settings.llm_api_key or "",
            model_name=settings.llm_model_name,
            embedding_model=settings.llm_embedding_model,
        )

    if settings.llm_provider == "openai":
        return OpenAIProvider(
            api_key=settings.llm_api_key or "",
            model_name=settings.llm_model_name,
            embedding_model=settings.llm_embedding_model,
        )

    if settings.llm_provider == "ollama":
        endpoint = settings.llm_endpoint or "http://localhost:11434"
        return OllamaProvider(endpoint=endpoint, model_name=settings.llm_model_name)

    if settings.llm_provider == "custom":
        if not settings.llm_endpoint:
            raise ValueError("LLM_ENDPOINT is required for custom provider.")
        return CustomProvider(
            endpoint=settings.llm_endpoint,
            api_key=settings.llm_api_key or "",
            model_name=settings.llm_model_name,
            embedding_model=settings.llm_embedding_model,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Dependency helper to build and cache a provider instance."""
    settings = get_settings()
    return build_llm_provider(settings)
