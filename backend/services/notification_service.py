"""
Multi-channel notification service.

Supports:
- Email notifications (SendGrid)
- Push notifications (for mobile)
- In-app notifications (stored in database)
- Webhook delivery
- Slack/Teams integration (future)
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import User, EmailNotification
from config import SENDGRID_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME

logger = logging.getLogger("notifications")


class NotificationChannel(str, Enum):
    """Available notification channels."""
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


class NotificationType(str, Enum):
    """Types of notifications."""
    MEETING_SUMMARY_READY = "meeting_summary_ready"
    ACTION_ITEM_DUE = "action_item_due"
    ACTION_ITEM_OVERDUE = "action_item_overdue"
    UPCOMING_MEETING = "upcoming_meeting"
    BRIEFING_READY = "briefing_ready"
    TRIAL_EXPIRING = "trial_expiring"
    TRIAL_EXPIRED = "trial_expired"
    WEEKLY_DIGEST = "weekly_digest"
    COMMITMENT_REMINDER = "commitment_reminder"
    TEAM_INVITE = "team_invite"
    SECURITY_ALERT = "security_alert"


@dataclass
class Notification:
    """Notification data structure."""
    type: NotificationType
    title: str
    message: str
    user_id: int
    data: Optional[Dict[str, Any]] = None
    channels: Optional[List[NotificationChannel]] = None
    priority: str = "normal"  # low, normal, high, urgent


class NotificationService:
    """
    Multi-channel notification service.

    Handles sending notifications through various channels based on
    user preferences and notification type.
    """

    def __init__(self, db: Session):
        self.db = db

    async def send(self, notification: Notification) -> Dict[str, Any]:
        """
        Send a notification through appropriate channels.

        Args:
            notification: Notification to send

        Returns:
            Dictionary with delivery status per channel
        """
        user = self.db.query(User).filter(User.id == notification.user_id).first()
        if not user:
            return {"error": "User not found"}

        # Determine channels based on user preferences and notification type
        channels = notification.channels or self._get_default_channels(notification.type, user)

        results = {}

        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    if user.email_notifications_enabled:
                        result = await self._send_email(notification, user)
                        results["email"] = result

                elif channel == NotificationChannel.PUSH:
                    result = await self._send_push(notification, user)
                    results["push"] = result

                elif channel == NotificationChannel.IN_APP:
                    result = await self._send_in_app(notification, user)
                    results["in_app"] = result

                elif channel == NotificationChannel.WEBHOOK:
                    result = await self._send_webhook(notification, user)
                    results["webhook"] = result

            except Exception as e:
                logger.error(f"Failed to send {channel} notification: {e}")
                results[channel.value] = {"success": False, "error": str(e)}

        return results

    def _get_default_channels(
        self,
        notification_type: NotificationType,
        user: User,
    ) -> List[NotificationChannel]:
        """Get default channels for a notification type based on user preferences."""
        channels = [NotificationChannel.IN_APP]  # Always store in-app

        # Email notifications based on type and preferences
        if notification_type in [
            NotificationType.MEETING_SUMMARY_READY,
            NotificationType.WEEKLY_DIGEST,
        ]:
            if user.email_summary_enabled:
                channels.append(NotificationChannel.EMAIL)

        elif notification_type in [
            NotificationType.ACTION_ITEM_DUE,
            NotificationType.ACTION_ITEM_OVERDUE,
            NotificationType.COMMITMENT_REMINDER,
        ]:
            if user.email_reminders_enabled:
                channels.append(NotificationChannel.EMAIL)

        elif notification_type in [
            NotificationType.TRIAL_EXPIRING,
            NotificationType.TRIAL_EXPIRED,
            NotificationType.SECURITY_ALERT,
            NotificationType.TEAM_INVITE,
        ]:
            # Always email for important notifications
            channels.append(NotificationChannel.EMAIL)

        return channels

    async def _send_email(self, notification: Notification, user: User) -> Dict:
        """Send email notification via SendGrid."""
        if not SENDGRID_API_KEY:
            return {"success": False, "error": "SendGrid not configured"}

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            # Build email
            subject = notification.title
            html_content = self._build_email_html(notification)

            message = Mail(
                from_email=Email(EMAIL_FROM, EMAIL_FROM_NAME),
                to_emails=To(user.email),
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)

            # Log email notification
            email_log = EmailNotification(
                user_id=user.id,
                email_type=notification.type.value,
                subject=subject,
                body=html_content,
                recipient_email=user.email,
                status="sent" if response.status_code == 202 else "failed",
                sent_at=datetime.utcnow(),
            )
            self.db.add(email_log)
            self.db.commit()

            return {
                "success": response.status_code == 202,
                "status_code": response.status_code,
            }

        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return {"success": False, "error": str(e)}

    async def _send_push(self, notification: Notification, user: User) -> Dict:
        """Send push notification (placeholder for mobile integration)."""
        # TODO: Integrate with Firebase Cloud Messaging or similar
        logger.info(f"Push notification queued for user {user.id}: {notification.title}")
        return {"success": True, "queued": True}

    async def _send_in_app(self, notification: Notification, user: User) -> Dict:
        """Store in-app notification in database."""
        from models import InAppNotification

        try:
            in_app = InAppNotification(
                user_id=user.id,
                type=notification.type.value,
                title=notification.title,
                message=notification.message,
                data=notification.data,
                priority=notification.priority,
            )
            self.db.add(in_app)
            self.db.commit()

            return {"success": True, "notification_id": in_app.id}
        except Exception as e:
            # Model might not exist yet
            logger.warning(f"In-app notification not saved: {e}")
            return {"success": False, "error": "In-app notifications not configured"}

    async def _send_webhook(self, notification: Notification, user: User) -> Dict:
        """Deliver notification via user's configured webhooks."""
        from models import Webhook
        import httpx

        webhooks = self.db.query(Webhook).filter(
            Webhook.user_id == user.id,
            Webhook.is_active == True,
            Webhook.events.contains([notification.type.value]),
        ).all()

        results = []
        for webhook in webhooks:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook.url,
                        json={
                            "event": notification.type.value,
                            "title": notification.title,
                            "message": notification.message,
                            "data": notification.data,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        headers=webhook.custom_headers or {},
                        timeout=10.0,
                    )
                    results.append({
                        "webhook_id": webhook.id,
                        "success": response.status_code < 400,
                        "status_code": response.status_code,
                    })
            except Exception as e:
                results.append({
                    "webhook_id": webhook.id,
                    "success": False,
                    "error": str(e),
                })

        return {"webhooks": results}

    def _build_email_html(self, notification: Notification) -> str:
        """Build HTML email content."""
        # Simple HTML template
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #d4af37; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #d4af37; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>ReadIn AI</h1>
                </div>
                <div class="content">
                    <h2>{notification.title}</h2>
                    <p>{notification.message}</p>
                </div>
                <div class="footer">
                    <p>You received this email because you have an account with ReadIn AI.</p>
                    <p><a href="https://www.getreadin.us/settings/notifications">Manage notification preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """


# =============================================================================
# NOTIFICATION TEMPLATES
# =============================================================================

def create_meeting_summary_notification(
    user_id: int,
    meeting_title: str,
    meeting_id: int,
) -> Notification:
    """Create notification for meeting summary ready."""
    return Notification(
        type=NotificationType.MEETING_SUMMARY_READY,
        title="Meeting Summary Ready",
        message=f"Your summary for '{meeting_title}' is ready to view.",
        user_id=user_id,
        data={"meeting_id": meeting_id},
    )


def create_action_item_due_notification(
    user_id: int,
    task_description: str,
    task_id: int,
    due_date: datetime,
) -> Notification:
    """Create notification for action item due."""
    return Notification(
        type=NotificationType.ACTION_ITEM_DUE,
        title="Action Item Due Soon",
        message=f"'{task_description[:50]}...' is due on {due_date.strftime('%B %d')}.",
        user_id=user_id,
        data={"task_id": task_id},
        priority="high",
    )


def create_trial_expiring_notification(
    user_id: int,
    days_remaining: int,
) -> Notification:
    """Create notification for trial expiring."""
    return Notification(
        type=NotificationType.TRIAL_EXPIRING,
        title="Your Trial is Ending Soon",
        message=f"You have {days_remaining} day(s) left in your free trial. Upgrade now to keep all features.",
        user_id=user_id,
        data={"days_remaining": days_remaining},
        priority="high",
    )


def create_briefing_ready_notification(
    user_id: int,
    meeting_title: str,
    briefing_id: int,
) -> Notification:
    """Create notification for pre-meeting briefing ready."""
    return Notification(
        type=NotificationType.BRIEFING_READY,
        title="Pre-Meeting Briefing Ready",
        message=f"Your briefing for '{meeting_title}' is ready. Review before your meeting.",
        user_id=user_id,
        data={"briefing_id": briefing_id},
    )


def create_security_alert_notification(
    user_id: int,
    alert_message: str,
    details: Dict = None,
) -> Notification:
    """Create security alert notification."""
    return Notification(
        type=NotificationType.SECURITY_ALERT,
        title="Security Alert",
        message=alert_message,
        user_id=user_id,
        data=details,
        priority="urgent",
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
    )
