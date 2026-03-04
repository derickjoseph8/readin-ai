"""
Meeting summary generation tasks.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

import anthropic

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# Prompt for extracting action items from meeting transcripts
ACTION_ITEM_EXTRACTION_PROMPT = """
Analyze this meeting transcript and extract action items.

For each action item, identify:
1. WHO is responsible
2. WHAT they need to do
3. WHEN it's due (if mentioned)

Transcript:
{transcript}

Return as JSON array:
[
  {{
    "assignee": "name or role",
    "task": "description",
    "due_date": "YYYY-MM-DD or null if not mentioned",
    "priority": "low/medium/high"
  }}
]

Important:
- Only extract clear, actionable items that were explicitly assigned or agreed upon
- If no clear assignee, use "User" as default
- Infer priority based on urgency language (ASAP, urgent = high; soon, this week = medium; no urgency = low)
- Return an empty array [] if no action items are found
- Return ONLY the JSON array, no additional text
"""


async def extract_action_items_with_ai(transcript: str) -> List[Dict[str, Any]]:
    """
    Extract action items from a meeting transcript using Claude AI.

    Args:
        transcript: The meeting transcript text

    Returns:
        List of action item dictionaries with keys: assignee, task, due_date, priority
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514")

    prompt = ACTION_ITEM_EXTRACTION_PROMPT.format(transcript=transcript)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.content[0].text

        # Handle JSON wrapped in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        action_items = json.loads(content.strip())

        # Validate and normalize the response
        validated_items = []
        for item in action_items:
            validated_item = {
                "assignee": item.get("assignee", "User"),
                "task": item.get("task", ""),
                "due_date": item.get("due_date"),
                "priority": item.get("priority", "medium").lower(),
            }

            # Skip items without a task description
            if not validated_item["task"]:
                continue

            # Normalize priority
            if validated_item["priority"] not in ["low", "medium", "high"]:
                validated_item["priority"] = "medium"

            # Validate due_date format or set to None
            if validated_item["due_date"]:
                try:
                    datetime.strptime(validated_item["due_date"], "%Y-%m-%d")
                except ValueError:
                    validated_item["due_date"] = None

            validated_items.append(validated_item)

        logger.info(f"Extracted {len(validated_items)} action items from transcript")
        return validated_items

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse action items JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Action item extraction failed: {e}")
        return []


def build_transcript_from_conversations(conversations) -> str:
    """
    Build a readable transcript from conversation objects.

    Args:
        conversations: List of Conversation model instances

    Returns:
        Formatted transcript string
    """
    lines = []
    for conv in conversations:
        time_str = conv.timestamp.strftime("%H:%M") if conv.timestamp else ""
        speaker = conv.speaker or "Unknown"
        lines.append(f"[{time_str}] {speaker}: {conv.heard_text}")
        if conv.response_text:
            lines.append(f"[{time_str}] AI Response: {conv.response_text}")
    return "\n".join(lines)


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
    Extract action items from meeting conversations using AI.

    This task analyzes the meeting transcript with Claude AI to identify
    actionable items, including who is responsible, what needs to be done,
    and any mentioned deadlines.
    """
    try:
        from database import SessionLocal
        from models import Meeting, Conversation, ActionItem

        db = SessionLocal()

        try:
            # Verify meeting exists and belongs to user
            meeting = db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user_id
            ).first()

            if not meeting:
                return {"success": False, "error": "Meeting not found"}

            # Get all conversations ordered by timestamp
            conversations = db.query(Conversation).filter(
                Conversation.meeting_id == meeting_id
            ).order_by(Conversation.timestamp).all()

            if not conversations:
                return {"success": False, "error": "No conversations to analyze"}

            # Build transcript from conversations
            transcript = build_transcript_from_conversations(conversations)

            if not transcript.strip():
                return {"success": False, "error": "Empty transcript"}

            # Extract action items using AI
            extracted_items = run_async(extract_action_items_with_ai(transcript))

            # Save extracted action items to database
            saved_items = []
            for item in extracted_items:
                # Parse due date if provided
                due_date = None
                if item.get("due_date"):
                    try:
                        due_date = datetime.strptime(item["due_date"], "%Y-%m-%d")
                    except ValueError:
                        pass

                # Create ActionItem record
                action_item = ActionItem(
                    meeting_id=meeting_id,
                    user_id=user_id,
                    assignee=item.get("assignee", "User"),
                    assignee_role="user" if item.get("assignee", "").lower() == "user" else "other",
                    description=item["task"],
                    due_date=due_date,
                    priority=item.get("priority", "medium"),
                    status="pending",
                )
                db.add(action_item)
                saved_items.append({
                    "assignee": action_item.assignee,
                    "description": action_item.description,
                    "due_date": item.get("due_date"),
                    "priority": action_item.priority,
                })

            db.commit()

            logger.info(
                f"Extracted and saved {len(saved_items)} action items "
                f"for meeting {meeting_id}"
            )

            return {
                "success": True,
                "meeting_id": meeting_id,
                "action_items": saved_items,
                "count": len(saved_items),
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to extract action items for meeting {meeting_id}: {e}")
        raise self.retry(exc=e, countdown=30)
