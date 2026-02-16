"""
Meeting summary generation tasks.
"""

from datetime import datetime
from typing import Optional
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_meeting_summary(
    self,
    meeting_id: int,
    user_id: int,
    send_email: bool = False
) -> dict:
    """
    Generate AI summary for a meeting.

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

        db = SessionLocal()

        try:
            # Get meeting and conversations
            meeting = db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            ).first()

            if not meeting:
                return {"success": False, "error": "Meeting not found"}

            conversations = db.query(Conversation).filter(
                Conversation.meeting_id == meeting_id
            ).order_by(Conversation.timestamp).all()

            if not conversations:
                return {"success": False, "error": "No conversations to summarize"}

            # Build transcript
            transcript = "\n".join([
                f"[{c.timestamp.strftime('%H:%M:%S')}] {c.speaker or 'Unknown'}: {c.content}"
                for c in conversations
            ])

            # Get user for AI customization
            user = db.query(User).filter(User.id == user_id).first()

            # TODO: Call AI service to generate summary
            # For now, create basic summary
            summary_text = f"Summary of {meeting.title or 'meeting'} with {len(conversations)} conversation turns."
            key_points = [
                f"Meeting type: {meeting.meeting_type}",
                f"Duration: {meeting.duration_seconds or 0} seconds",
                f"Participants: {meeting.participant_count or 'unknown'}",
            ]

            # Check for existing summary
            existing = db.query(MeetingSummary).filter(
                MeetingSummary.meeting_id == meeting_id
            ).first()

            if existing:
                existing.summary_text = summary_text
                existing.key_points = key_points
                existing.generated_at = datetime.utcnow()
                summary = existing
            else:
                summary = MeetingSummary(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    summary_text=summary_text,
                    key_points=key_points,
                    decisions_made=[],
                    topics_discussed=[meeting.meeting_type],
                    sentiment="neutral"
                )
                db.add(summary)

            db.commit()

            # Trigger email if requested
            if send_email and user and user.email:
                from workers.tasks.email_tasks import send_summary_email
                send_summary_email.delay(user_id, meeting_id, summary.id)

            logger.info(f"Generated summary for meeting {meeting_id}")

            return {
                "success": True,
                "meeting_id": meeting_id,
                "summary_id": summary.id,
                "summary_text": summary_text,
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
