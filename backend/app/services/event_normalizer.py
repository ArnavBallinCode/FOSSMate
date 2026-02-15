"""Platform event normalization helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.schemas import NormalizedEvent


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def normalize_github_event(
    event_type: str,
    delivery_id: str,
    payload: dict[str, Any],
) -> NormalizedEvent:
    """Normalize GitHub webhook payload into a platform-agnostic shape."""
    repo = payload.get("repository", {})
    pr = payload.get("pull_request", {})
    issue = payload.get("issue", {})
    sender = payload.get("sender", {})
    installation = payload.get("installation", {})

    occurred_at_raw = (
        payload.get("timestamp")
        or pr.get("updated_at")
        or pr.get("created_at")
        or issue.get("updated_at")
        or issue.get("created_at")
    )

    occurred_at = _now_utc()
    if isinstance(occurred_at_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = _now_utc()

    return NormalizedEvent(
        platform="github",
        delivery_id=delivery_id,
        event_type=event_type,
        action=str(payload.get("action", "unknown")),
        installation_id=installation.get("id"),
        repository_id=repo.get("id"),
        repository_owner=repo.get("owner", {}).get("login"),
        repository_name=repo.get("name"),
        repository_full_name=repo.get("full_name"),
        pr_number=pr.get("number"),
        pr_title=pr.get("title"),
        issue_number=issue.get("number"),
        issue_title=issue.get("title"),
        sender_login=sender.get("login"),
        head_sha=pr.get("head", {}).get("sha"),
        occurred_at=occurred_at,
        payload=payload,
    )


def normalize_gitlab_event(
    event_type: str,
    delivery_id: str,
    payload: dict[str, Any],
) -> NormalizedEvent:
    """Normalize GitLab webhook payload into a platform-agnostic shape."""
    project = payload.get("project", {})
    attrs = payload.get("object_attributes", {})
    user = payload.get("user", {})

    normalized_event_type = event_type.lower().replace(" hook", "").replace("_", "")
    action = str(attrs.get("action") or attrs.get("state") or "unknown")

    pr_number = attrs.get("iid") if normalized_event_type in {"mergerequest", "merge request"} else None
    issue_number = attrs.get("iid") if normalized_event_type in {"issue", "note"} else None

    occurred_at_raw = attrs.get("updated_at") or attrs.get("created_at")
    occurred_at = _now_utc()
    if isinstance(occurred_at_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_at_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = _now_utc()

    return NormalizedEvent(
        platform="gitlab",
        delivery_id=delivery_id,
        event_type=normalized_event_type,
        action=action,
        installation_id=None,
        repository_id=project.get("id"),
        repository_owner=project.get("namespace"),
        repository_name=project.get("name"),
        repository_full_name=project.get("path_with_namespace"),
        pr_number=pr_number,
        pr_title=attrs.get("title") if pr_number else None,
        issue_number=issue_number,
        issue_title=attrs.get("title") if issue_number else None,
        sender_login=user.get("username") or user.get("name"),
        head_sha=attrs.get("last_commit", {}).get("id"),
        occurred_at=occurred_at,
        payload=payload,
    )
