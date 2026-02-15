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
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.config import Settings, get_settings
from app.models.schemas import ProviderCapabilities


class LLMProvider(ABC):
    """Base interface for all LLM providers used by the application."""

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared capabilities for this provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider name."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model/deployment name."""

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
        self._model_name = model_name
        self._embedding_model = embedding_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider="gemini", supports_structured_output=False)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

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
    """OpenAI-compatible provider wrapper."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        embedding_model: str = "text-embedding-3-small",
        provider_name: str = "openai",
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers,
        )
        self._model_name = model_name
        self._embedding_model = embedding_model
        self._provider_name = provider_name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self._provider_name,
            supports_structured_output=True,
        )

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

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


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider wrapper."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment_name: str,
        api_version: str,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )
        self._deployment_name = deployment_name
        self._embedding_model = embedding_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider="azure_openai", supports_structured_output=True)

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    @property
    def model_name(self) -> str:
        return self._deployment_name

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._deployment_name,
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
            model=self._deployment_name,
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

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider="ollama", supports_structured_output=False)

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model_name

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


class FallbackLLMProvider(LLMProvider):
    """Provider wrapper that retries against configured fallbacks."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        if not providers:
            raise ValueError("FallbackLLMProvider requires at least one provider.")
        self._providers = providers

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._providers[0].capabilities

    @property
    def provider_name(self) -> str:
        return self._providers[0].provider_name

    @property
    def model_name(self) -> str:
        return self._providers[0].model_name

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        last_exc: Exception | None = None
        for provider in self._providers:
            try:
                return await provider.generate(prompt, system_prompt)
            except Exception as exc:  # pragma: no cover - runtime fallback safety
                last_exc = exc
                continue
        raise RuntimeError("All LLM providers failed to generate response") from last_exc

    async def stream_generate(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncIterator[str]:
        for provider in self._providers:
            try:
                async for token in provider.stream_generate(prompt, system_prompt):
                    yield token
                return
            except Exception:  # pragma: no cover - runtime fallback safety
                continue
        raise RuntimeError("All LLM providers failed to stream response")

    async def embed_text(self, text: str) -> list[float]:
        last_exc: Exception | None = None
        for provider in self._providers:
            try:
                return await provider.embed_text(text)
            except Exception as exc:  # pragma: no cover - runtime fallback safety
                last_exc = exc
                continue
        raise RuntimeError("All LLM providers failed to embed text") from last_exc


def _build_provider_from_values(
    provider_name: str,
    model_name: str,
    embedding_model: str,
    api_key: str | None,
    endpoint: str | None,
    settings: Settings,
) -> LLMProvider:
    if provider_name == "gemini":
        return GeminiProvider(
            api_key=api_key or "",
            model_name=model_name,
            embedding_model=embedding_model,
        )

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=api_key or "",
            model_name=model_name,
            embedding_model=embedding_model,
        )

    if provider_name == "openrouter":
        return OpenAIProvider(
            api_key=api_key or "",
            model_name=model_name,
            base_url=endpoint or settings.openrouter_endpoint,
            embedding_model=embedding_model,
            provider_name="openrouter",
            default_headers=settings.openrouter_headers,
        )

    if provider_name == "azure_openai":
        if not endpoint:
            raise ValueError("LLM_ENDPOINT is required for azure_openai provider.")
        return AzureOpenAIProvider(
            api_key=api_key or "",
            endpoint=endpoint,
            deployment_name=model_name,
            api_version=settings.azure_openai_api_version,
            embedding_model=embedding_model,
        )

    if provider_name == "ollama":
        return OllamaProvider(endpoint=endpoint or "http://localhost:11434", model_name=model_name)

    if provider_name == "custom":
        if not endpoint:
            raise ValueError("LLM_ENDPOINT is required for custom provider.")
        return OpenAIProvider(
            api_key=api_key or "",
            model_name=model_name,
            base_url=endpoint,
            embedding_model=embedding_model,
            provider_name="custom",
        )

    if provider_name == "deepseek":
        return OpenAIProvider(
            api_key=api_key or "",
            model_name=model_name,
            base_url=endpoint or settings.deepseek_endpoint,
            embedding_model=embedding_model,
            provider_name="deepseek",
        )

    if provider_name == "deepseek_r1":
        return OpenAIProvider(
            api_key=api_key or "",
            model_name=model_name,
            base_url=endpoint or settings.deepseek_endpoint,
            embedding_model=embedding_model,
            provider_name="deepseek_r1",
        )

    raise ValueError(f"Unsupported LLM provider: {provider_name}")


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Select provider implementation and optional fallback."""
    primary = _build_provider_from_values(
        provider_name=settings.llm_provider,
        model_name=settings.llm_model_name,
        embedding_model=settings.llm_embedding_model,
        api_key=settings.llm_api_key,
        endpoint=settings.llm_endpoint,
        settings=settings,
    )

    fallback_cfg = settings.fallback_llm_config
    if fallback_cfg is None:
        return primary

    fallback = _build_provider_from_values(
        provider_name=str(fallback_cfg["provider"]),
        model_name=str(fallback_cfg["model_name"]),
        embedding_model=settings.llm_embedding_model,
        api_key=fallback_cfg.get("api_key"),
        endpoint=fallback_cfg.get("endpoint"),
        settings=settings,
    )
    return FallbackLLMProvider([primary, fallback])


def provider_capability_matrix() -> dict[str, ProviderCapabilities]:
    """Return static capability declarations for supported providers."""
    return {
        "ollama": ProviderCapabilities(provider="ollama", supports_structured_output=False),
        "custom": ProviderCapabilities(provider="custom", supports_structured_output=True),
        "openai": ProviderCapabilities(provider="openai", supports_structured_output=True),
        "openrouter": ProviderCapabilities(provider="openrouter", supports_structured_output=True),
        "azure_openai": ProviderCapabilities(provider="azure_openai", supports_structured_output=True),
        "deepseek": ProviderCapabilities(provider="deepseek", supports_structured_output=True),
        "deepseek_r1": ProviderCapabilities(provider="deepseek_r1", supports_structured_output=True),
        "gemini": ProviderCapabilities(provider="gemini", supports_structured_output=False),
    }


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Dependency helper to build and cache a provider instance."""
    settings = get_settings()
    return build_llm_provider(settings)
