"""GitHub API interaction service placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GitHubService:
    """Stub GitHub service; implementation will be added in a later step."""

    app_id: str

    async def ping(self) -> str:
        """Simple async smoke test method."""
        return "github-service-ready"
