"""GitHub App authentication helper with installation token caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx
import jwt

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CachedInstallationToken:
    """Cached installation access token metadata."""

    token: str
    expires_at: datetime


class GitHubAppAuth:
    """Generate app JWT and fetch installation tokens from GitHub."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[int, CachedInstallationToken] = {}

    def build_app_jwt(self) -> str:
        """Create a short-lived GitHub App JWT."""
        now = datetime.now(tz=timezone.utc)
        payload = {
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": self._settings.github_app_id,
        }
        return jwt.encode(
            payload,
            self._settings.github_private_key_pem,
            algorithm="RS256",
        )

    async def get_installation_token(self, installation_id: int) -> str:
        """Return a cached installation token or request a new one."""
        now = datetime.now(tz=timezone.utc)
        cached = self._cache.get(installation_id)
        if cached and cached.expires_at > now + timedelta(minutes=2):
            return cached.token

        # Dev fallback when using a PAT and no private key is available.
        if self._settings.github_token and "TEST_KEY_REPLACE_ME" in self._settings.github_private_key_pem:
            return self._settings.github_token

        jwt_token = self.build_app_jwt()
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        token = str(data.get("token", ""))
        expires_at_raw = str(data.get("expires_at", ""))
        if not token or not expires_at_raw:
            raise RuntimeError("GitHub installation token response missing token/expiry.")

        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        self._cache[installation_id] = CachedInstallationToken(token=token, expires_at=expires_at)
        logger.debug("Refreshed GitHub installation token for installation=%s", installation_id)
        return token
