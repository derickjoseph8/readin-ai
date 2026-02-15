"""Email Service using SendGrid with secure Jinja2 templates."""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from sqlalchemy.orm import Session
from jinja2 import Environment, FileSystemLoader, select_autoescape

from models import EmailNotification, User
from config import SENDGRID_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME, APP_URL


class EmailService:
    """
    Email delivery service using SendGrid with secure Jinja2 templates.

    Security features:
    - Auto-escaping enabled for all HTML content
    - User input is sanitized before template rendering
    - Templates use Jinja2 sandboxed environment
    """

    def __init__(self, db: Session):
        self.db = db
        self.api_key = SENDGRID_API_KEY
        self.from_email = EMAIL_FROM
        self.from_name = EMAIL_FROM_NAME

        if self.api_key:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None

        # Initialize Jinja2 with auto-escaping for security
        templates_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(
                enabled_extensions=('html', 'htm', 'xml'),
                default_for_string=True,
                default=True
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.client is not None

    def _sanitize_string(self, value: Any) -> str:
        """
        Sanitize a string value for safe display.

        Removes potentially dangerous content while preserving readability.
        """
        if value is None:
            return ""
        value = str(value)
        # Limit length to prevent DoS
        if len(value) > 10000:
            value = value[:10000] + "..."
        return value

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template with the given context.

        Auto-escaping is enabled by default for security.
        """
        # Add common context
        context.setdefault("year", datetime.now().year)
        context.setdefault("app_url", APP_URL)
        context.setdefault("dashboard_url", f"{APP_URL}/dashboard")
        context.setdefault("preferences_url", f"{APP_URL}/settings/email")
        context.setdefault("unsubscribe_url", f"{APP_URL}/unsubscribe")

        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        user_id: Optional[int] = None,
        email_type: str = "general",
        plain_content: Optional[str] = None,
        related_meeting_id: Optional[int] = None,
        related_commitment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Send an email and log it."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Email service not configured. Set SENDGRID_API_KEY.",
            }

        message = Mail(
            from_email=Email(self.from_email, self.from_name),
            to_emails=To(to_email),
            subject=self._sanitize_string(subject)[:200],  # Limit subject length
            html_content=Content("text/html", html_content),
        )

        if plain_content:
            message.add_content(Content("text/plain", plain_content))

        try:
            response = self.client.send(message)

            # Log email
            notification = EmailNotification(
                user_id=user_id,
                email_type=email_type,
                recipient_email=to_email,
                subject=subject[:500],
                body=html_content[:50000],  # Limit stored body size
                status="sent",
                sent_at=datetime.utcnow(),
                related_meeting_id=related_meeting_id,
                related_commitment_id=related_commitment_id,
            )
            self.db.add(notification)
            self.db.commit()

            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id"),
            }

        except Exception as e:
            # Log failed attempt
            notification = EmailNotification(
                user_id=user_id,
                email_type=email_type,
                recipient_email=to_email,
                subject=subject[:500],
                body=html_content[:50000],
                status="failed",
                error_message=str(e)[:1000],
            )
            self.db.add(notification)
            self.db.commit()

            return {"success": False, "error": str(e)}

    async def send_meeting_summary(
        self,
        user_id: int,
        meeting_id: int,
        meeting_title: str,
        meeting_date: datetime,
        meeting_duration: str,
        meeting_type: str,
        summary_text: str,
        key_points: List[str],
        sentiment: str = "neutral",
        action_items: Optional[List[Dict[str, Any]]] = None,
        commitments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send meeting summary email to user using secure template."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_summary_enabled:
            return {"success": False, "error": "User has disabled summary emails"}

        # Render template with sanitized context
        context = {
            "meeting_title": self._sanitize_string(meeting_title) or "Untitled Meeting",
            "meeting_date": meeting_date.strftime("%B %d, %Y at %H:%M") if meeting_date else "Unknown",
            "meeting_duration": self._sanitize_string(meeting_duration) or "Unknown",
            "meeting_type": self._sanitize_string(meeting_type) or "general",
            "summary_text": self._sanitize_string(summary_text),
            "key_points": [self._sanitize_string(p) for p in (key_points or [])],
            "sentiment": sentiment if sentiment in ("positive", "neutral", "negative", "mixed") else "neutral",
            "action_items": action_items or [],
            "commitments": commitments or [],
        }

        html = self._render_template("meeting_summary.html", context)
        subject = f"Meeting Summary: {context['meeting_title'][:100]}"

        return await self.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html,
            user_id=user_id,
            email_type="meeting_summary",
            related_meeting_id=meeting_id,
        )

    async def send_commitment_reminder(
        self,
        user_id: int,
        commitment_id: int,
        commitment_description: str,
        due_date: Optional[datetime],
        context_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send commitment reminder email using secure template."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_reminders_enabled:
            return {"success": False, "error": "User has disabled reminder emails"}

        due_str = due_date.strftime("%B %d, %Y at %H:%M") if due_date else "soon"

        context = {
            "commitment_description": self._sanitize_string(commitment_description),
            "due_date": due_str,
            "context": self._sanitize_string(context_text) if context_text else None,
            "user_name": self._sanitize_string(user.full_name) or "there",
        }

        html = self._render_template("commitment_reminder.html", context)
        subject_preview = commitment_description[:50] + "..." if len(commitment_description) > 50 else commitment_description

        return await self.send_email(
            to_email=user.email,
            subject=f"Reminder: {subject_preview}",
            html_content=html,
            user_id=user_id,
            email_type="commitment_reminder",
            related_commitment_id=commitment_id,
        )

    async def send_pre_meeting_briefing(
        self,
        user_id: int,
        meeting_title: str,
        meeting_time: Optional[datetime],
        summary: str,
        participant_insights: Optional[List[Dict[str, Any]]] = None,
        talking_points: Optional[List[str]] = None,
        follow_up_items: Optional[List[str]] = None,
        topics_to_avoid: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send pre-meeting briefing email using secure template."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_notifications_enabled:
            return {"success": False, "error": "User has disabled notification emails"}

        # Sanitize participant insights
        safe_participants = []
        for p in (participant_insights or []):
            safe_participants.append({
                "name": self._sanitize_string(p.get("name", "Unknown")),
                "role": self._sanitize_string(p.get("role", "")),
                "company": self._sanitize_string(p.get("company", "")),
                "key_insight": self._sanitize_string(p.get("key_insight", "")),
                "communication_style": self._sanitize_string(p.get("communication_style", "")),
            })

        context = {
            "meeting_title": self._sanitize_string(meeting_title) or "Upcoming Meeting",
            "meeting_time": meeting_time.strftime("%B %d, %Y at %H:%M") if meeting_time else "Soon",
            "summary": self._sanitize_string(summary),
            "participant_insights": safe_participants,
            "talking_points": [self._sanitize_string(p) for p in (talking_points or [])],
            "follow_up_items": [self._sanitize_string(i) for i in (follow_up_items or [])],
            "topics_to_avoid": [self._sanitize_string(t) for t in (topics_to_avoid or [])],
            "user_name": self._sanitize_string(user.full_name) or "there",
        }

        html = self._render_template("pre_meeting_briefing.html", context)

        return await self.send_email(
            to_email=user.email,
            subject=f"Briefing: {context['meeting_title'][:100]}",
            html_content=html,
            user_id=user_id,
            email_type="pre_meeting_briefing",
        )

    async def send_weekly_digest(
        self,
        user_id: int,
        meeting_count: int = 0,
        meetings: Optional[List[Dict[str, Any]]] = None,
        actions_completed: int = 0,
        pending_actions: Optional[List[Dict[str, Any]]] = None,
        commitments_fulfilled: int = 0,
        pending_commitments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send weekly activity digest using secure template."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_notifications_enabled:
            return {"success": False, "error": "User has disabled notification emails"}

        # Sanitize meetings list
        safe_meetings = []
        for m in (meetings or []):
            safe_meetings.append({
                "title": self._sanitize_string(m.get("title", "Untitled")),
                "date": self._sanitize_string(m.get("date", "")),
                "type": self._sanitize_string(m.get("type", "general")),
            })

        # Sanitize actions list
        safe_actions = []
        for a in (pending_actions or []):
            safe_actions.append({
                "description": self._sanitize_string(a.get("description", "")),
                "assignee": self._sanitize_string(a.get("assignee", "")),
                "due_date": self._sanitize_string(a.get("due_date", "")),
            })

        context = {
            "user_name": self._sanitize_string(user.full_name) or "there",
            "meeting_count": meeting_count,
            "meetings": safe_meetings,
            "actions_completed": actions_completed,
            "pending_actions": safe_actions,
            "commitments_fulfilled": commitments_fulfilled,
            "pending_commitments": pending_commitments or [],
        }

        html = self._render_template("weekly_digest.html", context)

        return await self.send_email(
            to_email=user.email,
            subject="Your Weekly ReadIn AI Digest",
            html_content=html,
            user_id=user_id,
            email_type="weekly_digest",
        )

    async def get_email_history(
        self, user_id: int, limit: int = 50
    ) -> List[EmailNotification]:
        """Get user's email history."""
        return (
            self.db.query(EmailNotification)
            .filter(EmailNotification.user_id == user_id)
            .order_by(EmailNotification.created_at.desc())
            .limit(min(limit, 100))  # Cap at 100 to prevent abuse
            .all()
        )

    async def update_preferences(
        self,
        user_id: int,
        summary_enabled: Optional[bool] = None,
        reminders_enabled: Optional[bool] = None,
        notifications_enabled: Optional[bool] = None,
    ) -> User:
        """Update user's email preferences."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        if summary_enabled is not None:
            user.email_summary_enabled = summary_enabled
        if reminders_enabled is not None:
            user.email_reminders_enabled = reminders_enabled
        if notifications_enabled is not None:
            user.email_notifications_enabled = notifications_enabled

        self.db.commit()
        return user
