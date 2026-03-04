"""Meeting Summary Generator using Claude AI.

This module provides comprehensive AI-powered meeting analysis including:
- Executive summary generation
- Key point extraction with context
- Decision detection and tracking
- Risk identification and mitigation suggestions
- Follow-up action recommendations
- Action item summary with priorities
- Participant contribution analysis
- Meeting effectiveness scoring
"""

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
from services.language_service import get_localized_prompt_suffix, get_fallback_message


# Enhanced prompts for comprehensive meeting analysis
COMPREHENSIVE_SUMMARY_PROMPT = """You are an expert meeting analyst. Analyze this meeting transcript and provide a comprehensive, actionable summary.

Meeting Context:
- Type: {meeting_type}
- Title: {title}
- Duration: {duration}

Transcript:
{transcript}

Provide a thorough analysis in the following JSON format. Be specific, actionable, and focus on extracting maximum value from this meeting:

{{
    "summary": "A comprehensive 2-3 paragraph executive summary that captures the meeting's purpose, key discussions, outcomes, and overall trajectory. Include context about what was achieved and what remains to be done.",

    "key_points": [
        {{
            "point": "Clear, specific key point from the meeting",
            "context": "Brief context explaining why this point matters",
            "speaker": "Who raised this point (if identifiable)"
        }}
    ],

    "decisions_made": [
        {{
            "decision": "Specific decision that was made",
            "rationale": "Why this decision was made (if discussed)",
            "owner": "Who is responsible for implementing this decision",
            "timeline": "When this should be implemented (if mentioned)"
        }}
    ],

    "action_items": [
        {{
            "assignee": "Who is responsible (use 'User' if it's the meeting participant)",
            "description": "Specific, actionable task description",
            "due_date": "YYYY-MM-DD or null if not specified",
            "priority": "high/medium/low",
            "context": "Brief context about why this action is needed"
        }}
    ],

    "commitments": [
        {{
            "description": "What the user committed to do",
            "due_date": "YYYY-MM-DD or null if not specified",
            "to_whom": "Who the commitment was made to"
        }}
    ],

    "risks_identified": [
        {{
            "risk": "Description of the risk or concern",
            "severity": "high/medium/low",
            "mitigation": "Suggested mitigation strategy"
        }}
    ],

    "follow_up_suggestions": [
        {{
            "suggestion": "Specific follow-up action to take",
            "reason": "Why this follow-up is important",
            "timing": "When this should be done (e.g., 'within 24 hours', 'next week')"
        }}
    ],

    "action_item_summary": "A concise 1-2 sentence executive summary of all action items, highlighting the most critical ones and overall workload.",

    "topics_discussed": ["topic1", "topic2", "topic3"],

    "participant_contributions": {{
        "topic_name": ["participant1", "participant2"]
    }},

    "meeting_effectiveness": {{
        "score": 1-10,
        "strengths": ["What went well in this meeting"],
        "improvements": ["What could be improved for future meetings"]
    }},

    "next_steps": [
        "Prioritized list of recommended next steps",
        "Based on the meeting outcomes"
    ],

    "sentiment": "positive/neutral/negative/mixed",

    "follow_up_needed": true/false,

    "key_quotes": [
        {{
            "quote": "Important or memorable quote from the meeting",
            "speaker": "Who said it",
            "significance": "Why this quote matters"
        }}
    ]
}}{language_instruction}

Important guidelines:
1. Be specific and actionable - avoid generic summaries
2. Extract concrete decisions, not just discussions
3. Identify risks proactively, even if not explicitly mentioned
4. Suggest follow-ups that would add value
5. Rate meeting effectiveness honestly
6. Capture commitments that were made verbally
7. Prioritize action items by urgency and impact
8. Note participant contributions to topics when identifiable
"""

# Meeting type-specific analysis prompts
MEETING_TYPE_PROMPTS = {
    "interview": """Additional interview-specific analysis:
- Evaluate the candidate's/interviewer's key strengths demonstrated
- Note any red flags or concerns
- Identify follow-up questions that should be asked
- Assess cultural fit indicators
- Summarize compensation/benefits discussed""",

    "sales": """Additional sales meeting analysis:
- Identify buying signals and objections
- Note decision-maker engagement level
- Extract budget/timeline indicators
- Suggest next steps in the sales process
- Highlight competitive mentions""",

    "team_meeting": """Additional team meeting analysis:
- Track blockers mentioned and their owners
- Note team morale indicators
- Identify resource constraints
- Highlight cross-team dependencies
- Summarize sprint/project status""",

    "one_on_one": """Additional 1:1 meeting analysis:
- Note feedback exchanged (positive and constructive)
- Identify career development discussions
- Track commitments from both parties
- Highlight relationship-building moments
- Summarize growth opportunities discussed""",

    "tv_appearance": """Additional media appearance analysis:
- Evaluate key message delivery
- Note memorable sound bites
- Identify questions that were handled well/poorly
- Suggest improvements for future appearances
- Track any commitments made publicly""",
}


class SummaryGenerator:
    """Generate comprehensive AI-powered meeting summaries.

    This class uses Claude AI to analyze meeting transcripts and extract:
    - Executive summaries with context
    - Key points with speaker attribution
    - Decisions with rationale and owners
    - Action items with priorities
    - Risks and mitigation strategies
    - Follow-up suggestions
    - Meeting effectiveness scoring
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv(
            "SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514"
        )

    async def generate_summary(self, meeting_id: int, language: Optional[str] = None) -> MeetingSummary:
        """Generate a comprehensive meeting summary with enhanced AI analysis.

        This method extracts:
        - Executive summary with context
        - Key points with speaker attribution
        - Decisions with owners and timelines
        - Action items with priorities
        - Risks and mitigation strategies
        - Follow-up suggestions
        - Meeting effectiveness scoring
        - Next steps recommendations

        Args:
            meeting_id: The meeting to summarize
            language: Language code for the response (defaults to user preference)

        Returns:
            MeetingSummary object with all analysis fields populated
        """
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # Get user's preferred language if not specified
        if language is None:
            user = self.db.query(User).filter(User.id == meeting.user_id).first()
            language = getattr(user, 'preferred_language', 'en') or 'en' if user else 'en'

        # Get all conversations from meeting
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.meeting_id == meeting_id)
            .order_by(Conversation.timestamp)
            .all()
        )

        if not conversations:
            raise ValueError("No conversations in meeting")

        # Build conversation transcript
        transcript = self._build_transcript(conversations)

        # Generate comprehensive summary with Claude
        summary_data = await self._generate_with_claude(
            transcript,
            meeting.meeting_type,
            meeting.title,
            language,
            meeting.duration_seconds
        )

        # Create or update summary with all enhanced fields
        existing = (
            self.db.query(MeetingSummary)
            .filter(MeetingSummary.meeting_id == meeting_id)
            .first()
        )

        if existing:
            # Update existing summary with all fields
            existing.summary_text = summary_data["summary"]
            existing.key_points = summary_data["key_points"]
            existing.sentiment = summary_data.get("sentiment", "neutral")
            existing.topics_discussed = summary_data.get("topics_discussed", [])
            existing.decisions_made = summary_data.get("decisions_made", [])
            # Enhanced fields
            existing.risks_identified = summary_data.get("risks_identified", [])
            existing.follow_up_suggestions = summary_data.get("follow_up_suggestions", [])
            existing.action_item_summary = summary_data.get("action_item_summary", "")
            existing.participant_contributions = summary_data.get("participant_contributions", {})
            existing.meeting_effectiveness_score = summary_data.get("meeting_effectiveness_score")
            existing.next_steps = summary_data.get("next_steps", [])
            summary = existing
        else:
            # Create new summary with all fields
            summary = MeetingSummary(
                meeting_id=meeting_id,
                user_id=meeting.user_id,
                summary_text=summary_data["summary"],
                key_points=summary_data["key_points"],
                sentiment=summary_data.get("sentiment", "neutral"),
                topics_discussed=summary_data.get("topics_discussed", []),
                decisions_made=summary_data.get("decisions_made", []),
                # Enhanced fields
                risks_identified=summary_data.get("risks_identified", []),
                follow_up_suggestions=summary_data.get("follow_up_suggestions", []),
                action_item_summary=summary_data.get("action_item_summary", ""),
                participant_contributions=summary_data.get("participant_contributions", {}),
                meeting_effectiveness_score=summary_data.get("meeting_effectiveness_score"),
                next_steps=summary_data.get("next_steps", []),
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

        # Fire Zapier trigger for summary_generated
        try:
            from integrations.zapier import fire_summary_generated
            user = self.db.query(User).filter(User.id == meeting.user_id).first()
            if user:
                import asyncio
                asyncio.create_task(fire_summary_generated(self.db, summary, meeting, user))
        except Exception as e:
            # Don't fail if Zapier integration fails
            pass

        return summary

    def _build_transcript(self, conversations: List[Conversation]) -> str:
        """Build transcript from conversations."""
        lines = []
        for conv in conversations:
            time_str = conv.timestamp.strftime("%H:%M") if conv.timestamp else ""
            speaker = conv.speaker or "Unknown"
            lines.append(f"[{time_str}] {speaker}: {conv.heard_text}")
            if conv.response_text:
                lines.append(f"[{time_str}] AI Response: {conv.response_text}")
        return "\n".join(lines)

    async def _generate_with_claude(
        self, transcript: str, meeting_type: str, title: Optional[str], language: str = "en", duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive summary using Claude AI.

        Args:
            transcript: The meeting transcript text
            meeting_type: Type of meeting (interview, sales, team_meeting, etc.)
            title: Meeting title
            language: Language code for response
            duration_seconds: Meeting duration in seconds

        Returns:
            Comprehensive analysis dictionary with all summary components
        """
        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        # Format duration for display
        duration_str = "Unknown"
        if duration_seconds:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            if hours > 0:
                duration_str = f"{hours}h {minutes}m"
            else:
                duration_str = f"{minutes} minutes"

        # Build the comprehensive prompt
        prompt = COMPREHENSIVE_SUMMARY_PROMPT.format(
            meeting_type=meeting_type or 'general',
            title=title or 'Untitled Meeting',
            duration=duration_str,
            transcript=transcript,
            language_instruction=language_instruction
        )

        # Add meeting type-specific analysis if available
        if meeting_type and meeting_type in MEETING_TYPE_PROMPTS:
            prompt += f"\n\n{MEETING_TYPE_PROMPTS[meeting_type]}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased for comprehensive analysis
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Post-process and normalize the response
            return self._normalize_summary_response(data)

        except json.JSONDecodeError as e:
            print(f"Summary JSON parsing error: {e}")
            return self._get_fallback_response(language)
        except Exception as e:
            print(f"Summary generation error: {e}")
            return self._get_fallback_response(language)

    def _normalize_summary_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate the AI response.

        Ensures all expected fields exist and have correct types.
        Extracts simple lists from structured data where needed.
        """
        # Extract simple key points list from structured data
        key_points = data.get("key_points", [])
        if key_points and isinstance(key_points[0], dict):
            # Convert structured key points to simple strings with context
            key_points = [
                f"{kp.get('point', '')} - {kp.get('context', '')}" if kp.get('context')
                else kp.get('point', str(kp))
                for kp in key_points
            ]

        # Extract simple decisions list from structured data
        decisions = data.get("decisions_made", [])
        if decisions and isinstance(decisions[0], dict):
            decisions = [
                f"{d.get('decision', '')} (Owner: {d.get('owner', 'TBD')})"
                for d in decisions
            ]

        # Extract risks as simple list
        risks = data.get("risks_identified", [])
        if risks and isinstance(risks[0], dict):
            risks = [
                f"{r.get('risk', '')} [{r.get('severity', 'medium')}] - Mitigation: {r.get('mitigation', 'TBD')}"
                for r in risks
            ]

        # Extract follow-up suggestions as simple list
        follow_ups = data.get("follow_up_suggestions", [])
        if follow_ups and isinstance(follow_ups[0], dict):
            follow_ups = [
                f"{f.get('suggestion', '')} ({f.get('timing', 'ASAP')})"
                for f in follow_ups
            ]

        # Extract meeting effectiveness score
        effectiveness = data.get("meeting_effectiveness", {})
        effectiveness_score = None
        if isinstance(effectiveness, dict):
            effectiveness_score = effectiveness.get("score")
        elif isinstance(effectiveness, int):
            effectiveness_score = effectiveness

        return {
            "summary": data.get("summary", ""),
            "key_points": key_points,
            "decisions_made": decisions,
            "action_items": data.get("action_items", []),
            "commitments": data.get("commitments", []),
            "risks_identified": risks,
            "follow_up_suggestions": follow_ups,
            "action_item_summary": data.get("action_item_summary", ""),
            "topics_discussed": data.get("topics_discussed", []),
            "participant_contributions": data.get("participant_contributions", {}),
            "meeting_effectiveness_score": effectiveness_score,
            "next_steps": data.get("next_steps", []),
            "sentiment": data.get("sentiment", "neutral"),
            "follow_up_needed": data.get("follow_up_needed", False),
            "key_quotes": data.get("key_quotes", []),
        }

    def _get_fallback_response(self, language: str) -> Dict[str, Any]:
        """Get a fallback response when AI generation fails."""
        return {
            "summary": get_fallback_message("summary_unavailable", language),
            "key_points": [],
            "decisions_made": [],
            "action_items": [],
            "commitments": [],
            "risks_identified": [],
            "follow_up_suggestions": [],
            "action_item_summary": "",
            "topics_discussed": [],
            "participant_contributions": {},
            "meeting_effectiveness_score": None,
            "next_steps": [],
            "sentiment": "neutral",
            "follow_up_needed": False,
            "key_quotes": [],
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
