"""Email Service using SendGrid."""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType
import base64
from sqlalchemy.orm import Session

from models import EmailNotification, User


class EmailService:
    """Email delivery service using SendGrid."""

    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("EMAIL_FROM", "noreply@getreadin.ai")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "ReadIn AI")

        if self.api_key:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None

    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return self.client is not None

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        user_id: Optional[int] = None,
        email_type: str = "general",
        plain_content: Optional[str] = None,
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
            subject=subject,
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
                recipient=to_email,
                subject=subject,
                body=html_content,
                status="sent",
                sent_at=datetime.utcnow(),
                sendgrid_message_id=response.headers.get("X-Message-Id"),
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
                recipient=to_email,
                subject=subject,
                body=html_content,
                status="failed",
                error_message=str(e),
            )
            self.db.add(notification)
            self.db.commit()

            return {"success": False, "error": str(e)}

    async def send_meeting_summary(
        self, user_id: int, meeting_id: int, summary_content: Dict[str, str]
    ) -> Dict[str, Any]:
        """Send meeting summary email to user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_summary_enabled:
            return {"success": False, "error": "User has disabled summary emails"}

        html = self._wrap_in_template(
            summary_content["body"],
            "Meeting Summary",
        )

        return await self.send_email(
            to_email=user.email,
            subject=summary_content["subject"],
            html_content=html,
            user_id=user_id,
            email_type="meeting_summary",
        )

    async def send_commitment_reminder(
        self, user_id: int, commitment_description: str, due_date: datetime
    ) -> Dict[str, Any]:
        """Send commitment reminder email."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        if not user.email_reminders_enabled:
            return {"success": False, "error": "User has disabled reminder emails"}

        due_str = due_date.strftime("%B %d, %Y at %H:%M") if due_date else "soon"

        html_body = f"""
        <h2>Commitment Reminder</h2>
        <p>This is a reminder about your upcoming commitment:</p>

        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 18px; margin: 0;">{commitment_description}</p>
            <p style="color: #666; margin-top: 10px;">Due: {due_str}</p>
        </div>

        <p>Don't forget to follow through on this commitment!</p>
        """

        html = self._wrap_in_template(html_body, "Commitment Reminder")

        return await self.send_email(
            to_email=user.email,
            subject=f"Reminder: {commitment_description[:50]}...",
            html_content=html,
            user_id=user_id,
            email_type="commitment_reminder",
        )

    async def send_pre_meeting_briefing(
        self, user_id: int, briefing: Dict[str, Any], meeting_title: str
    ) -> Dict[str, Any]:
        """Send pre-meeting briefing email."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Build briefing HTML
        talking_points = ""
        if briefing.get("talking_points"):
            talking_points = "<h3>Talking Points</h3><ul>"
            for point in briefing["talking_points"]:
                talking_points += f"<li>{point}</li>"
            talking_points += "</ul>"

        participant_insights = ""
        if briefing.get("participant_insights"):
            participant_insights = "<h3>Participant Insights</h3>"
            for p in briefing["participant_insights"]:
                participant_insights += f"""
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
                    <strong>{p.get('name', 'Unknown')}</strong>
                    <p>{p.get('key_insight', '')}</p>
                </div>
                """

        follow_ups = ""
        if briefing.get("follow_up_items"):
            follow_ups = "<h3>Items to Follow Up</h3><ul>"
            for item in briefing["follow_up_items"]:
                follow_ups += f"<li>{item}</li>"
            follow_ups += "</ul>"

        html_body = f"""
        <h2>Pre-Meeting Briefing: {meeting_title}</h2>

        <h3>Summary</h3>
        <p>{briefing.get('summary', 'No summary available')}</p>

        {participant_insights}
        {talking_points}
        {follow_ups}

        <hr>
        <p><em>Good luck with your meeting!</em></p>
        """

        html = self._wrap_in_template(html_body, "Pre-Meeting Briefing")

        return await self.send_email(
            to_email=user.email,
            subject=f"Briefing: {meeting_title}",
            html_content=html,
            user_id=user_id,
            email_type="pre_meeting_briefing",
        )

    async def send_weekly_digest(
        self, user_id: int, digest_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send weekly activity digest."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        meetings_html = ""
        if digest_data.get("meetings"):
            meetings_html = "<h3>This Week's Meetings</h3><ul>"
            for meeting in digest_data["meetings"]:
                meetings_html += f"<li>{meeting['title']} - {meeting['date']}</li>"
            meetings_html += "</ul>"

        actions_html = ""
        if digest_data.get("pending_actions"):
            actions_html = "<h3>Pending Action Items</h3><ul>"
            for action in digest_data["pending_actions"]:
                actions_html += f"<li>{action['description']}</li>"
            actions_html += "</ul>"

        html_body = f"""
        <h2>Your Weekly ReadIn AI Digest</h2>

        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Week at a Glance</h3>
            <p>Meetings: {digest_data.get('meeting_count', 0)}</p>
            <p>Action Items Completed: {digest_data.get('actions_completed', 0)}</p>
            <p>Commitments Fulfilled: {digest_data.get('commitments_fulfilled', 0)}</p>
        </div>

        {meetings_html}
        {actions_html}

        <p>Keep up the great work!</p>
        """

        html = self._wrap_in_template(html_body, "Weekly Digest")

        return await self.send_email(
            to_email=user.email,
            subject="Your Weekly ReadIn AI Digest",
            html_content=html,
            user_id=user_id,
            email_type="weekly_digest",
        )

    def _wrap_in_template(self, body: str, title: str) -> str:
        """Wrap content in email template."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        h2 {{
            color: #1a1a1a;
            border-bottom: 2px solid #fbbf24;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #4a4a4a;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        .header {{
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #1a1a1a;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #ffffff;
            padding: 30px;
            border: 1px solid #e5e5e5;
            border-top: none;
        }}
        .footer {{
            background: #1a1a1a;
            color: #999;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 8px 8px;
        }}
        .footer a {{
            color: #fbbf24;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0;">ReadIn AI</h1>
    </div>
    <div class="content">
        {body}
    </div>
    <div class="footer">
        <p>This email was sent by ReadIn AI</p>
        <p><a href="https://getreadin.ai">getreadin.ai</a> | <a href="https://getreadin.ai/unsubscribe">Unsubscribe</a></p>
    </div>
</body>
</html>
"""

    async def get_email_history(
        self, user_id: int, limit: int = 50
    ) -> List[EmailNotification]:
        """Get user's email history."""
        return (
            self.db.query(EmailNotification)
            .filter(EmailNotification.user_id == user_id)
            .order_by(EmailNotification.created_at.desc())
            .limit(limit)
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
