"""Core review orchestration: summarization, suggestions, and scoring."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any

from app.models.schemas import (
    FileChangeSummary,
    NormalizedEvent,
    ReviewResult,
    ReviewSuggestion,
    ScoreCard,
)
from app.services.github_service import GitHubService
from app.services.llm_service import LLMProvider

logger = logging.getLogger(__name__)

REVIEW_CATEGORIES = ("feature", "fix", "refactor", "docs", "test", "chore", "mixed")


@dataclass(slots=True)
class ReviewService:
    """Generate review artifacts for PR and issue events."""

    llm_provider: LLMProvider
    github_service: GitHubService

    async def build_pr_review(self, event: NormalizedEvent) -> ReviewResult:
        """Build PR summary, file summaries, suggestions, and scorecard."""
        if not event.repository_full_name or event.pr_number is None:
            raise ValueError("Pull request review requires repository_full_name and pr_number.")

        files = await self._load_pr_files(event)
        category = self._categorize_pr(event.pr_title or "", files)

        pr_summary = await self._generate_pr_summary(event, category, files)
        file_summaries = await self._summarize_files(files)
        suggestions = await self._generate_suggestions(event, files)
        score_card = await self._score_pr(event, files, suggestions)

        major_files = [item["filename"] for item in files[:5] if "filename" in item]
        sources = [item.path for item in file_summaries]

        return ReviewResult(
            category=category,
            pr_summary=pr_summary,
            major_files=major_files,
            file_summaries=file_summaries,
            suggestions=suggestions,
            score_card=score_card,
            sources=sources,
            model_used=self.llm_provider.model_name,
        )

    async def summarize_issue(self, event: NormalizedEvent) -> str:
        """Summarize a newly opened issue."""
        issue_title = event.issue_title or "Untitled issue"
        issue_body = str(event.payload.get("issue", {}).get("body", ""))
        prompt = (
            "Summarize this GitHub issue in 3 concise bullets for maintainers.\n"
            f"Title: {issue_title}\n"
            f"Body:\n{issue_body}"
        )
        try:
            return await self.llm_provider.generate(prompt)
        except Exception:  # pragma: no cover - runtime resilience
            logger.exception("Issue summarization failed; falling back to heuristic summary.")
            return f"- {issue_title}\n- Review details and assign ownership\n- Suggest labels"

    async def onboarding_reply(self, event: NormalizedEvent) -> str:
        """Generate contributor onboarding guidance comment."""
        repo = event.repository_full_name or "this repository"
        return (
            f"Thanks for offering to contribute to **{repo}**. "
            "Please read `README` and `CONTRIBUTING` first, share your proposed approach, "
            "and wait for maintainer confirmation before starting implementation."
        )

    async def _load_pr_files(self, event: NormalizedEvent) -> list[dict[str, Any]]:
        if event.installation_id is None:
            return []
        try:
            return await self.github_service.list_pull_request_files(
                repository_full_name=event.repository_full_name or "",
                pr_number=event.pr_number or 0,
                installation_id=event.installation_id,
            )
        except Exception:  # pragma: no cover - runtime resilience
            logger.exception(
                "Unable to fetch PR files for %s#%s",
                event.repository_full_name,
                event.pr_number,
            )
            return []

    def _categorize_pr(self, title: str, files: list[dict[str, Any]]) -> str:
        title_l = title.lower()
        file_paths = " ".join(str(item.get("filename", "")).lower() for item in files)

        if any(word in title_l for word in ("fix", "bug", "hotfix")):
            return "fix"
        if any(word in title_l for word in ("refactor", "cleanup")):
            return "refactor"
        if any(word in title_l for word in ("test", "spec")):
            return "test"
        if any(word in title_l for word in ("docs", "readme", "documentation")) or "docs/" in file_paths:
            return "docs"
        if any(word in title_l for word in ("chore", "ci", "build", "deps")):
            return "chore"
        if re.search(r"\b(add|implement|introduce|create|feat)\b", title_l):
            return "feature"
        return "mixed"

    async def _generate_pr_summary(
        self,
        event: NormalizedEvent,
        category: str,
        files: list[dict[str, Any]],
    ) -> str:
        file_names = [str(item.get("filename", "")) for item in files[:20]]
        prompt = (
            "Generate a concise pull request summary for maintainers. Include:\n"
            "1) what changed\n"
            "2) risk/impact\n"
            "3) suggested review focus\n"
            "Keep to <= 6 bullets.\n\n"
            f"PR title: {event.pr_title}\n"
            f"Category: {category}\n"
            f"Changed files: {json.dumps(file_names)}\n"
        )
        try:
            return await self.llm_provider.generate(prompt)
        except Exception:  # pragma: no cover - runtime resilience
            logger.exception("PR summary generation failed; using fallback summary.")
            fallback_files = ", ".join(file_names[:5]) if file_names else "(file list unavailable)"
            return (
                f"- Category: {category}\n"
                f"- Title: {event.pr_title or 'Untitled PR'}\n"
                f"- Major files: {fallback_files}\n"
                "- Review focus: core logic changes, tests, and edge-case handling"
            )

    async def _summarize_files(self, files: list[dict[str, Any]]) -> list[FileChangeSummary]:
        summaries: list[FileChangeSummary] = []
        for item in files[:25]:
            path = str(item.get("filename", "unknown"))
            status = str(item.get("status", "modified"))
            additions = int(item.get("additions", 0) or 0)
            deletions = int(item.get("deletions", 0) or 0)
            patch = str(item.get("patch", ""))
            prompt = (
                "Summarize this code diff in one sentence plus risk level (low/medium/high).\n"
                f"File: {path}\n"
                f"Patch:\n{patch[:3000]}"
            )
            summary_text = ""
            risk = "low"
            try:
                summary_text = await self.llm_provider.generate(prompt)
                if "high" in summary_text.lower():
                    risk = "high"
                elif "medium" in summary_text.lower():
                    risk = "medium"
            except Exception:  # pragma: no cover - runtime resilience
                summary_text = (
                    f"{path}: {status} (+{additions}/-{deletions}). "
                    "Review logic and test impact."
                )
                if additions + deletions > 250:
                    risk = "high"
                elif additions + deletions > 80:
                    risk = "medium"

            summaries.append(
                FileChangeSummary(
                    path=path,
                    status=status,
                    additions=additions,
                    deletions=deletions,
                    summary=summary_text.strip(),
                    risk=risk,
                )
            )
        return summaries

    async def _generate_suggestions(
        self,
        event: NormalizedEvent,
        files: list[dict[str, Any]],
    ) -> list[ReviewSuggestion]:
        prompt = (
            "Provide up to 5 non-blocking code review suggestions for this PR. "
            "Respond as JSON list with fields: title, details, severity(low|medium|high), file_path(optional).\n"
            f"PR title: {event.pr_title}\n"
            f"Files: {[item.get('filename') for item in files[:25]]}"
        )

        try:
            raw = await self.llm_provider.generate(prompt)
            parsed = json.loads(self._extract_json(raw))
            suggestions: list[ReviewSuggestion] = []
            if isinstance(parsed, list):
                for item in parsed[:5]:
                    if not isinstance(item, dict):
                        continue
                    suggestions.append(
                        ReviewSuggestion(
                            file_path=item.get("file_path"),
                            title=str(item.get("title", "Review suggestion")),
                            details=str(item.get("details", "No details provided.")),
                            severity=str(item.get("severity", "medium")).lower(),
                        )
                    )
            if suggestions:
                return suggestions
        except Exception:  # pragma: no cover - runtime resilience
            logger.exception("Review suggestion generation failed; using heuristic fallback.")

        fallback_file = files[0].get("filename") if files else None
        return [
            ReviewSuggestion(
                file_path=fallback_file,
                title="Validate edge cases",
                details="Review boundary conditions and error handling for modified paths.",
                severity="medium",
            ),
            ReviewSuggestion(
                title="Add or update tests",
                details="Ensure behavior changes are covered by tests to prevent regressions.",
                severity="medium",
            ),
        ]

    async def _score_pr(
        self,
        event: NormalizedEvent,
        files: list[dict[str, Any]],
        suggestions: list[ReviewSuggestion],
    ) -> ScoreCard:
        size = sum(int(item.get("additions", 0) or 0) + int(item.get("deletions", 0) or 0) for item in files)
        tests_touched = any("test" in str(item.get("filename", "")).lower() for item in files)
        severe_findings = sum(1 for s in suggestions if s.severity == "high")

        correctness = 8.5 if tests_touched else 7.2
        readability = 8.0
        maintainability = 7.8

        if size > 400:
            readability -= 0.8
            maintainability -= 0.8
        if severe_findings:
            correctness -= min(1.5, severe_findings * 0.5)
            maintainability -= min(1.0, severe_findings * 0.3)

        correctness = max(0.0, min(10.0, correctness))
        readability = max(0.0, min(10.0, readability))
        maintainability = max(0.0, min(10.0, maintainability))
        overall = round((correctness + readability + maintainability) / 3.0, 2)

        return ScoreCard(
            correctness=round(correctness, 2),
            readability=round(readability, 2),
            maintainability=round(maintainability, 2),
            overall=overall,
            advisory_only=True,
        )

    @staticmethod
    def _extract_json(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        start = raw.find("[")
        end = raw.rfind("]")
        if start >= 0 and end > start:
            return raw[start : end + 1]
        return raw
