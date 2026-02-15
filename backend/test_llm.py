"""Simple provider smoke test for FOSSMate LLM abstraction."""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.services.llm_service import build_llm_provider

ISSUE_TEXT = """
Title: Add first-time contributor docs
Body:
We should add a CONTRIBUTING.md section for first-time contributors.
It should include setup steps, coding style, and how to run tests.
""".strip()


async def main() -> None:
    settings = get_settings()
    provider = build_llm_provider(settings)
    prompt = f"Summarize this GitHub issue in 3 bullet points:\n\n{ISSUE_TEXT}"
    result = await provider.generate(prompt)
    print(result.strip())


if __name__ == "__main__":
    asyncio.run(main())
