"""Meeting Summary Generator using Claude AI."""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic
from sqlalchemy.orm import Session

from models import (
    Meeting,
    Conversation,
    MeetingSummary,
    ActionItem,
    Commitment,
    User,
)


class SummaryGenerator:
    """Generate meeting summaries and extract action items."""

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv(
            "SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514"
        )

    async def generate_summary(self, meeting_id: int) -> MeetingSummary:
        """Generate a comprehensive meeting summary."""
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # Get all conversations from meeting
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.meeting_id == meeting_id)
            .order_by(Conversation.created_at)
            .all()
        )

        if not conversations:
            raise ValueError("No conversations in meeting")

        # Build conversation transcript
        transcript = self._build_transcript(conversations)

        # Generate summary with Claude
        summary_data = await self._generate_with_claude(
            transcript, meeting.meeting_type, meeting.title
        )

        # Create or update summary
        existing = (
            self.db.query(MeetingSummary)
            .filter(MeetingSummary.meeting_id == meeting_id)
            .first()
        )

        if existing:
            existing.summary_text = summary_data["summary"]
            existing.key_points = summary_data["key_points"]
            existing.sentiment = summary_data.get("sentiment", "neutral")
            existing.generated_at = datetime.utcnow()
            summary = existing
        else:
            summary = MeetingSummary(
                meeting_id=meeting_id,
                summary_text=summary_data["summary"],
                key_points=summary_data["key_points"],
                sentiment=summary_data.get("sentiment", "neutral"),
                generated_at=datetime.utcnow(),
            )
            self.db.add(summary)

        # Extract and store action items
        await self._store_action_items(
            meeting_id, meeting.user_id, summary_data.get("action_items", [])
        )

        # Extract and store commitments
        await self._store_commitments(
            meeting_id, meeting.user_id, summary_data.get("commitments", [])
        )

        self.db.commit()
        return summary

    def _build_transcript(self, conversations: List[Conversation]) -> str:
        """Build transcript from conversations."""
        lines = []
        for conv in conversations:
            timestamp = conv.created_at.strftime("%H:%M") if conv.created_at else ""
            speaker = conv.speaker or "Unknown"
            lines.append(f"[{timestamp}] {speaker}: {conv.heard_text}")
            if conv.response_text:
                lines.append(f"[{timestamp}] AI Response: {conv.response_text}")
        return "\n".join(lines)

    async def _generate_with_claude(
        self, transcript: str, meeting_type: str, title: Optional[str]
    ) -> Dict[str, Any]:
        """Generate summary using Claude."""
        prompt = f"""Analyze this meeting transcript and provide a comprehensive summary.

Meeting Type: {meeting_type or 'general'}
Title: {title or 'Untitled Meeting'}

Transcript:
{transcript}

Provide analysis in this JSON format:
{{
    "summary": "A 2-3 paragraph executive summary of the meeting",
    "key_points": [
        "Key point 1",
        "Key point 2",
        "Key point 3"
    ],
    "action_items": [
        {{
            "assignee": "Who is responsible (or 'User' if the user)",
            "description": "What needs to be done",
            "due_date": "YYYY-MM-DD or null if not specified",
            "priority": "high/medium/low"
        }}
    ],
    "commitments": [
        {{
            "description": "What the user committed to do",
            "due_date": "YYYY-MM-DD or null if not specified"
        }}
    ],
    "sentiment": "positive/neutral/negative/mixed",
    "topics_discussed": ["topic1", "topic2"],
    "decisions_made": ["decision 1", "decision 2"],
    "follow_up_needed": true/false
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())

        except Exception as e:
            print(f"Summary generation error: {e}")
            return {
                "summary": "Unable to generate summary.",
                "key_points": [],
                "action_items": [],
                "commitments": [],
                "sentiment": "neutral",
            }

    async def _store_action_items(
        self, meeting_id: int, user_id: int, items: List[Dict]
    ) -> None:
        """Store extracted action items."""
        for item in items:
            due_date = None
            if item.get("due_date"):
                try:
                    due_date = datetime.strptime(item["due_date"], "%Y-%m-%d")
                except ValueError:
                    pass

            action = ActionItem(
                meeting_id=meeting_id,
                user_id=user_id,
                assignee=item.get("assignee", "User"),
                assignee_role=item.get("assignee_role"),
                description=item["description"],
                due_date=due_date,
                priority=item.get("priority", "medium"),
                status="pending",
            )
            self.db.add(action)

    async def _store_commitments(
        self, meeting_id: int, user_id: int, commitments: List[Dict]
    ) -> None:
        """Store extracted user commitments."""
        for comm in commitments:
            due_date = None
            if comm.get("due_date"):
                try:
                    due_date = datetime.strptime(comm["due_date"], "%Y-%m-%d")
                except ValueError:
                    pass

            commitment = Commitment(
                meeting_id=meeting_id,
                user_id=user_id,
                description=comm["description"],
                due_date=due_date,
                status="pending",
            )
            self.db.add(commitment)

    async def generate_email_content(self, meeting_id: int) -> Dict[str, str]:
        """Generate email-ready summary content."""
        summary = (
            self.db.query(MeetingSummary)
            .filter(MeetingSummary.meeting_id == meeting_id)
            .first()
        )

        if not summary:
            summary = await self.generate_summary(meeting_id)

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()

        # Get action items
        action_items = (
            self.db.query(ActionItem)
            .filter(ActionItem.meeting_id == meeting_id)
            .all()
        )

        # Get commitments
        commitments = (
            self.db.query(Commitment)
            .filter(Commitment.meeting_id == meeting_id)
            .all()
        )

        # Format key points
        key_points_html = ""
        if summary.key_points:
            key_points_html = "<ul>"
            for point in summary.key_points:
                key_points_html += f"<li>{point}</li>"
            key_points_html += "</ul>"

        # Format action items
        actions_html = ""
        if action_items:
            actions_html = "<h3>Action Items</h3><ul>"
            for action in action_items:
                due = f" (Due: {action.due_date.strftime('%Y-%m-%d')})" if action.due_date else ""
                actions_html += f"<li><strong>{action.assignee}:</strong> {action.description}{due}</li>"
            actions_html += "</ul>"

        # Format commitments
        commits_html = ""
        if commitments:
            commits_html = "<h3>Your Commitments</h3><ul>"
            for comm in commitments:
                due = f" (Due: {comm.due_date.strftime('%Y-%m-%d')})" if comm.due_date else ""
                commits_html += f"<li>{comm.description}{due}</li>"
            commits_html += "</ul>"

        subject = f"Meeting Summary: {meeting.title or 'Your Meeting'}"
        if meeting.ended_at:
            subject += f" - {meeting.ended_at.strftime('%B %d, %Y')}"

        body = f"""
<h2>{meeting.title or 'Meeting Summary'}</h2>
<p><em>{meeting.meeting_type or 'General Meeting'} | {meeting.started_at.strftime('%B %d, %Y %H:%M') if meeting.started_at else ''}</em></p>

<h3>Summary</h3>
<p>{summary.summary_text}</p>

<h3>Key Points</h3>
{key_points_html}

{actions_html}

{commits_html}

<hr>
<p><small>Generated by ReadIn AI</small></p>
"""

        return {"subject": subject, "body": body}

    async def get_meeting_insights(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get insights from user's recent meetings."""
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        meetings = (
            self.db.query(Meeting)
            .filter(Meeting.user_id == user_id, Meeting.started_at >= since)
            .all()
        )

        summaries = (
            self.db.query(MeetingSummary)
            .join(Meeting)
            .filter(Meeting.user_id == user_id, Meeting.started_at >= since)
            .all()
        )

        # Aggregate insights
        total_meetings = len(meetings)
        sentiments = [s.sentiment for s in summaries if s.sentiment]

        positive = sentiments.count("positive")
        negative = sentiments.count("negative")
        neutral = sentiments.count("neutral")

        # Count action items
        action_count = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.user_id == user_id,
                ActionItem.created_at >= since,
            )
            .count()
        )

        completed_actions = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.user_id == user_id,
                ActionItem.created_at >= since,
                ActionItem.status == "completed",
            )
            .count()
        )

        return {
            "period_days": days,
            "total_meetings": total_meetings,
            "sentiment_breakdown": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "mixed": len(sentiments) - positive - negative - neutral,
            },
            "action_items": {
                "total": action_count,
                "completed": completed_actions,
                "completion_rate": (
                    completed_actions / action_count if action_count > 0 else 0
                ),
            },
        }
