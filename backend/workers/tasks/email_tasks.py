"""
Email notification tasks.
"""

import logging
from typing import Optional

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, rate_limit="10/m")
def send_email(
    self,
    to_email: str,
    subject: str,
    template_name: str,
    template_data: dict
) -> dict:
    """
    Send an email using the email service.

    Args:
        to_email: Recipient email
        subject: Email subject
        template_name: Jinja2 template name
        template_data: Data to pass to template

    Returns:
        dict with send status
    """
    try:
        from services.email_service import email_service

        success = email_service.send_template_email(
            to_email=to_email,
            subject=subject,
            template_name=template_name,
            template_data=template_data
        )

        if success:
            logger.info(f"Email sent to {to_email}: {subject}")
            return {"success": True, "to": to_email}
        else:
            logger.warning(f"Failed to send email to {to_email}")
            return {"success": False, "error": "Send failed"}

    except Exception as e:
        logger.error(f"Email task failed: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=2)
def send_summary_email(
    self,
    user_id: int,
    meeting_id: int,
    summary_id: int
) -> dict:
    """
    Send meeting summary email to user.
    """
    try:
        from database import SessionLocal
        from models import User, Meeting, MeetingSummary
        from services.email_service import email_service

        db = SessionLocal()

        try:
            user = db.query(User).filter(User.id == user_id).first()
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            summary = db.query(MeetingSummary).filter(MeetingSummary.id == summary_id).first()

            if not all([user, meeting, summary]):
                return {"success": False, "error": "Data not found"}

            if not user.email:
                return {"success": False, "error": "User has no email"}

            # Send email
            success = email_service.send_meeting_summary(
                to_email=user.email,
                user_name=user.full_name or user.email,
                meeting_title=meeting.title or "Your Meeting",
                summary_text=summary.summary_text,
                key_points=summary.key_points or [],
                action_items=[],
                meeting_date=meeting.started_at,
                duration_minutes=(meeting.duration_seconds or 0) // 60
            )

            if success:
                logger.info(f"Summary email sent for meeting {meeting_id} to {user.email}")
                return {"success": True, "meeting_id": meeting_id}
            else:
                return {"success": False, "error": "Send failed"}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Summary email task failed: {e}")
        raise self.retry(exc=e, countdown=120)


@celery_app.task(bind=True, max_retries=2)
def send_briefing_email(
    self,
    user_id: int,
    briefing_id: int
) -> dict:
    """
    Send pre-meeting briefing email.
    """
    try:
        from database import SessionLocal
        from models import User, PreMeetingBriefing
        from services.email_service import email_service

        db = SessionLocal()

        try:
            user = db.query(User).filter(User.id == user_id).first()
            briefing = db.query(PreMeetingBriefing).filter(
                PreMeetingBriefing.id == briefing_id
            ).first()

            if not all([user, briefing]):
                return {"success": False, "error": "Data not found"}

            if not user.email:
                return {"success": False, "error": "User has no email"}

            # Send email
            success = email_service.send_pre_meeting_briefing(
                to_email=user.email,
                user_name=user.full_name or user.email,
                meeting_title=briefing.title or "Upcoming Meeting",
                briefing_content=briefing.content,
                participants=briefing.participants or [],
                meeting_time=briefing.scheduled_time,
                key_topics=briefing.key_topics or []
            )

            if success:
                logger.info(f"Briefing email sent for {briefing_id} to {user.email}")
                return {"success": True, "briefing_id": briefing_id}
            else:
                return {"success": False, "error": "Send failed"}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Briefing email task failed: {e}")
        raise self.retry(exc=e, countdown=120)


@celery_app.task
def send_welcome_email(user_id: int) -> dict:
    """Send welcome email to new user."""
    try:
        from database import SessionLocal
        from models import User
        from services.email_service import email_service

        db = SessionLocal()

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.email:
                return {"success": False, "error": "User not found"}

            success = email_service.send_welcome_email(
                to_email=user.email,
                user_name=user.full_name or "there"
            )

            return {"success": success, "user_id": user_id}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Welcome email failed: {e}")
        return {"success": False, "error": str(e)}
