"""Notification channel abstraction for review reports."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import smtplib
from email.mime.text import MIMEText

from app.config import Settings
from app.models.schemas import NotificationPayload

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NotificationService:
    """Send notifications for completed review runs."""

    settings: Settings

    async def send_review_notification(self, payload: NotificationPayload) -> None:
        """Send email report when feature is enabled."""
        if not self.settings.email_enabled or not payload.recipients:
            return

        message = MIMEText(payload.body_text, "plain", "utf-8")
        message["Subject"] = payload.subject
        message["From"] = self.settings.email_from or "fossmate@localhost"
        message["To"] = ", ".join(payload.recipients)

        try:
            with smtplib.SMTP(self.settings.email_smtp_host, self.settings.email_smtp_port) as smtp:
                smtp.starttls()
                if self.settings.email_smtp_username and self.settings.email_smtp_password:
                    smtp.login(self.settings.email_smtp_username, self.settings.email_smtp_password)
                smtp.sendmail(
                    self.settings.email_from or "fossmate@localhost",
                    payload.recipients,
                    message.as_string(),
                )
        except Exception:  # pragma: no cover - runtime safety
            logger.exception("Failed to send review notification email.")
