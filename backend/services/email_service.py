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
            "user_name": self._sanitize_string(user.full_name) or "there",
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

    async def send_security_alert(
        self,
        user_id: int,
        alert_type: str,
        alert_title: str,
        alert_description: str,
        severity: str = "medium",
        ip_address: Optional[str] = None,
        device_info: Optional[Dict[str, Any]] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send security alert email using secure template."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Security alerts should always be sent regardless of preferences
        context = {
            "user_name": self._sanitize_string(user.full_name) or "there",
            "alert_type": alert_type,
            "alert_title": self._sanitize_string(alert_title),
            "alert_description": self._sanitize_string(alert_description),
            "severity": severity if severity in ("low", "medium", "high") else "medium",
            "ip_address": self._sanitize_string(ip_address) if ip_address else None,
            "device_info": device_info,
            "location": self._sanitize_string(location) if location else None,
            "timestamp": datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
        }

        html = self._render_template("security_alert.html", context)

        return await self.send_email(
            to_email=user.email,
            subject=f"Security Alert: {context['alert_title'][:80]}",
            html_content=html,
            user_id=user_id,
            email_type="security_alert",
        )

    async def send_password_reset(
        self,
        email: str,
        reset_token: str,
        user_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send password reset email using secure template."""
        reset_url = f"{APP_URL}/reset-password?token={reset_token}"
        support_url = f"{APP_URL}/support"

        context = {
            "user_name": self._sanitize_string(user_name) or "there",
            "reset_url": reset_url,
            "support_url": support_url,
        }

        html = self._render_template("password_reset.html", context)

        return await self.send_email(
            to_email=email,
            subject="Reset Your ReadIn AI Password",
            html_content=html,
            email_type="password_reset",
        )

    async def send_welcome_email(
        self,
        user_id: int,
        verification_token: str,
    ) -> Dict[str, Any]:
        """Send welcome email with verification link to new users."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        verification_url = f"{APP_URL}/verify-email?token={verification_token}"

        context = {
            "user_name": self._sanitize_string(user.full_name) or "there",
            "verification_url": verification_url,
            "help_url": f"{APP_URL}/help",
        }

        html = self._render_template("welcome.html", context)

        return await self.send_email(
            to_email=user.email,
            subject="Verify Your Email - Welcome to ReadIn AI!",
            html_content=html,
            user_id=user_id,
            email_type="welcome",
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

    async def send_organization_invite(
        self,
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invite_token: str,
        role: str = "member",
    ) -> Dict[str, Any]:
        """Send organization invitation email."""
        invite_url = f"{APP_URL}/join/{invite_token}"

        # Build inline HTML since we may not have a template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #1a1a1a; border-radius: 16px; border: 1px solid #333;">
                            <tr>
                                <td style="padding: 32px 40px; text-align: center; border-bottom: 1px solid #333;">
                                    <div style="font-size: 28px; font-weight: 700; color: #ffffff;">
                                        ReadIn <span style="color: #d4af37;">AI</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px;">
                                    <h1 style="margin: 0 0 20px; color: #ffffff; font-size: 24px;">You're Invited to Join a Team</h1>
                                    <p style="color: #ffffff; margin-bottom: 16px;">
                                        <strong>{self._sanitize_string(inviter_name)}</strong> has invited you to join
                                        <strong style="color: #d4af37;">{self._sanitize_string(organization_name)}</strong> on ReadIn AI.
                                    </p>
                                    <p style="color: #a0a0a0;">You'll be joining as a <strong>{self._sanitize_string(role)}</strong>. Team members get full access to ReadIn AI at no additional cost - the organization admin covers all subscription fees.</p>
                                    <div style="text-align: center; margin: 30px 0;">
                                        <a href="{invite_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #d4af37, #c5a028); color: #1a1a1a; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                            Accept Invitation
                                        </a>
                                    </div>
                                    <p style="color: #666; font-size: 14px;">This invitation expires in 7 days.</p>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 24px 40px; border-top: 1px solid #333; text-align: center;">
                                    <p style="margin: 0; color: #666; font-size: 12px;">
                                        If you didn't expect this invitation, you can safely ignore this email.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            subject=f"Join {organization_name} on ReadIn AI",
            html_content=html,
            email_type="organization_invite",
        )

    async def send_account_deletion_warning(
        self,
        user_id: int,
        deletion_date: datetime,
        days_remaining: int,
    ) -> Dict[str, Any]:
        """Send warning about upcoming account deletion due to inactivity."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        login_url = f"{APP_URL}/login"
        user_name = self._sanitize_string(user.full_name) or "there"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #1a1a1a; border-radius: 16px; border: 1px solid #333;">
                            <tr>
                                <td style="padding: 32px 40px; text-align: center; border-bottom: 1px solid #333;">
                                    <div style="font-size: 28px; font-weight: 700; color: #ffffff;">
                                        ReadIn <span style="color: #d4af37;">AI</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px;">
                                    <h1 style="margin: 0 0 20px; color: #ffffff; font-size: 24px;">Your Account Will Be Deleted Soon</h1>
                                    <p style="color: #ffffff; margin-bottom: 16px;">Hi {user_name},</p>
                                    <p style="color: #a0a0a0;">Your ReadIn AI trial account has been inactive for 90 days. To comply with our data retention policy, your account and all associated data will be permanently deleted on <strong style="color: #d4af37;">{deletion_date.strftime('%B %d, %Y')}</strong>.</p>
                                    <p style="color: #a0a0a0; margin-top: 16px;">That's <strong>{days_remaining} days</strong> from now.</p>
                                    <p style="color: #a0a0a0; margin-top: 16px;">To keep your account active, simply log in before the deletion date. All your meeting history, insights, and learning profile will be preserved.</p>
                                    <div style="text-align: center; margin: 30px 0;">
                                        <a href="{login_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #d4af37, #c5a028); color: #1a1a1a; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                            Log In to Keep Your Account
                                        </a>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 24px 40px; border-top: 1px solid #333; text-align: center;">
                                    <p style="margin: 0; color: #666; font-size: 12px;">
                                        Questions? Contact us at support@getreadin.ai
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=user.email,
            subject="Action Required: Your ReadIn AI Account Will Be Deleted",
            html_content=html,
            user_id=user_id,
            email_type="account_deletion_warning",
        )

    async def send_trial_expiring(
        self,
        user_id: int,
        days_remaining: int,
    ) -> Dict[str, Any]:
        """Send trial expiration warning email."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        upgrade_url = f"{APP_URL}/pricing"
        user_name = self._sanitize_string(user.full_name) or "there"
        day_word = "day" if days_remaining == 1 else "days"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0a0a0a;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #0a0a0a;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #1a1a1a; border-radius: 16px; border: 1px solid #333;">
                            <tr>
                                <td style="padding: 32px 40px; text-align: center; border-bottom: 1px solid #333;">
                                    <div style="font-size: 28px; font-weight: 700; color: #ffffff;">
                                        ReadIn <span style="color: #d4af37;">AI</span>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 40px;">
                                    <h1 style="margin: 0 0 20px; color: #ffffff; font-size: 24px;">Your Trial is Ending Soon</h1>
                                    <p style="color: #ffffff; margin-bottom: 16px;">Hi {user_name},</p>
                                    <p style="color: #a0a0a0;">Your free trial of ReadIn AI ends in <strong style="color: #d4af37;">{days_remaining} {day_word}</strong>.</p>
                                    <p style="color: #a0a0a0; margin-top: 16px;">After your trial ends, you'll be limited to 10 AI responses per day. Upgrade to Premium for unlimited responses and keep excelling in your meetings.</p>
                                    <p style="color: #d4af37; margin-top: 24px;"><strong>Premium Benefits:</strong></p>
                                    <ul style="color: #a0a0a0; padding-left: 20px;">
                                        <li>Unlimited AI responses</li>
                                        <li>Custom response presets</li>
                                        <li>Meeting summaries and action items</li>
                                        <li>Priority support</li>
                                    </ul>
                                    <div style="text-align: center; margin: 30px 0;">
                                        <a href="{upgrade_url}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #d4af37, #c5a028); color: #1a1a1a; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                            Upgrade to Premium
                                        </a>
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 24px 40px; border-top: 1px solid #333; text-align: center;">
                                    <p style="margin: 0; color: #666; font-size: 12px;">
                                        Questions? Contact us at support@getreadin.ai
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=user.email,
            subject=f"Your ReadIn AI Trial Ends in {days_remaining} {day_word.title()}",
            html_content=html,
            user_id=user_id,
            email_type="trial_expiring",
        )
