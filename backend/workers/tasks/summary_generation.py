"""
Meeting summary generation tasks.
"""

import asyncio
from datetime import datetime
from typing import Optional
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async functions in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, max_retries=3)
def generate_meeting_summary(
    self,
    meeting_id: int,
    user_id: int,
    send_email: bool = False
) -> dict:
    """
    Generate AI summary for a meeting using Claude.

    Args:
        meeting_id: Meeting ID to summarize
        user_id: User who owns the meeting
        send_email: Whether to send summary via email

    Returns:
        dict with summary data
    """
    try:
        # Import here to avoid circular imports
        from database import SessionLocal
        from models import Meeting, Conversation, MeetingSummary, User
        from services.summary_generator import SummaryGenerator

        db = SessionLocal()

        try:
            # Get meeting
            meeting = db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            ).first()

            if not meeting:
                return {"success": False, "error": "Meeting not found"}

            # Check if there are conversations
            conv_count = db.query(Conversation).filter(
                Conversation.meeting_id == meeting_id
            ).count()

            if conv_count == 0:
                return {"success": False, "error": "No conversations to summarize"}

            # Get user for language preference
            user = db.query(User).filter(User.id == user_id).first()
            language = getattr(user, 'preferred_language', 'en') or 'en'

            # Use the AI-powered SummaryGenerator
            generator = SummaryGenerator(db)
            summary = run_async(generator.generate_summary(meeting_id, language))

            logger.info(f"Generated AI summary for meeting {meeting_id}")

            # Trigger email if requested
            if send_email and user and user.email:
                from workers.tasks.email_tasks import send_summary_email
                send_summary_email.delay(user_id, meeting_id, summary.id)
                logger.info(f"Queued summary email for meeting {meeting_id}")

            return {
                "success": True,
                "meeting_id": meeting_id,
                "summary_id": summary.id,
                "summary_text": summary.summary_text,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to generate summary for meeting {meeting_id}: {e}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, max_retries=2)
def extract_action_items(
    self,
    meeting_id: int,
    user_id: int
) -> dict:
    """
    Extract action items from meeting conversations.
    """
    try:
        from database import SessionLocal
        from models import Meeting, Conversation, ActionItem

        db = SessionLocal()

        try:
            conversations = db.query(Conversation).filter(
                Conversation.meeting_id == meeting_id
            ).all()

            if not conversations:
                return {"success": False, "error": "No conversations"}

            # TODO: Use AI to extract action items
            # For now, return empty list
            action_items = []

            return {
                "success": True,
                "meeting_id": meeting_id,
                "action_items": action_items,
                "count": len(action_items),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to extract action items: {e}")
        raise self.retry(exc=e, countdown=30)
