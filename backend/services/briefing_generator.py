"""Pre-Meeting Briefing Generator."""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import (
    ParticipantMemory,
    Meeting,
    Conversation,
    Topic,
    User,
    Commitment,
    ActionItem,
)
from services.language_service import get_localized_prompt_suffix, get_fallback_message


class BriefingGenerator:
    """Generate pre-meeting briefings with context and preparation materials."""

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv(
            "SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514"
        )

    async def generate_briefing(
        self,
        user_id: int,
        participant_names: List[str],
        meeting_context: Optional[str] = None,
        meeting_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive pre-meeting briefing."""
        user = self.db.query(User).filter(User.id == user_id).first()

        # Use user's preferred language if not specified
        if language is None and user:
            language = getattr(user, 'preferred_language', 'en') or 'en'
        elif language is None:
            language = 'en'

        # Get participant memories
        participant_data = []
        for name in participant_names:
            memory = await self.get_participant_context(user_id, name)
            if memory:
                participant_data.append(memory)

        # Get user's recent topics
        recent_topics = await self._get_recent_topics(user_id)

        # Get pending commitments
        pending_commitments = await self._get_pending_commitments(user_id)

        # Get pending action items
        pending_actions = await self._get_pending_actions(user_id)

        # Generate briefing with Claude
        briefing = await self._generate_with_claude(
            user=user,
            participants=participant_data,
            topics=recent_topics,
            commitments=pending_commitments,
            actions=pending_actions,
            context=meeting_context,
            meeting_type=meeting_type,
            language=language,
        )

        return briefing

    async def get_participant_context(
        self, user_id: int, participant_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get context about a participant from memory."""
        # Search by name (case insensitive, partial match)
        memory = (
            self.db.query(ParticipantMemory)
            .filter(
                ParticipantMemory.user_id == user_id,
                ParticipantMemory.participant_name.ilike(f"%{participant_name}%"),
            )
            .first()
        )

        if not memory:
            return None

        return {
            "name": memory.participant_name,
            "role": memory.participant_role,
            "company": memory.company,
            "key_points": memory.key_points or [],
            "topics_discussed": memory.topics_discussed or [],
            "last_interaction": (
                memory.last_interaction_at.isoformat()
                if memory.last_interaction_at
                else None
            ),
            "interaction_count": memory.interaction_count,
            "notes": memory.notes,
        }

    async def _get_recent_topics(self, user_id: int, limit: int = 10) -> List[str]:
        """Get user's recent discussion topics."""
        topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id)
            .order_by(Topic.last_discussed_at.desc())
            .limit(limit)
            .all()
        )
        return [t.name for t in topics]

    async def _get_pending_commitments(self, user_id: int) -> List[Dict]:
        """Get user's pending commitments."""
        commitments = (
            self.db.query(Commitment)
            .filter(
                Commitment.user_id == user_id,
                Commitment.status == "pending",
            )
            .order_by(Commitment.due_date)
            .limit(10)
            .all()
        )

        return [
            {
                "description": c.description,
                "due_date": c.due_date.isoformat() if c.due_date else None,
            }
            for c in commitments
        ]

    async def _get_pending_actions(self, user_id: int) -> List[Dict]:
        """Get pending action items assigned to user."""
        actions = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.user_id == user_id,
                ActionItem.status == "pending",
                or_(
                    ActionItem.assignee == "User",
                    ActionItem.assignee.ilike("%me%"),
                ),
            )
            .order_by(ActionItem.due_date)
            .limit(10)
            .all()
        )

        return [
            {
                "description": a.description,
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "priority": a.priority,
            }
            for a in actions
        ]

    async def _generate_with_claude(
        self,
        user: User,
        participants: List[Dict],
        topics: List[str],
        commitments: List[Dict],
        actions: List[Dict],
        context: Optional[str],
        meeting_type: Optional[str],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Generate briefing using Claude."""
        profession_context = ""
        if user.profession:
            profession_context = f"User's profession: {user.profession.name}"

        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Generate a comprehensive pre-meeting briefing.

{profession_context}

Meeting Type: {meeting_type or 'General'}
Additional Context: {context or 'None provided'}

Known Participants:
{json.dumps(participants, indent=2) if participants else 'No prior history with participants'}

User's Recent Topics:
{json.dumps(topics) if topics else 'No recent topics'}

Pending Commitments to Follow Up:
{json.dumps(commitments, indent=2) if commitments else 'None'}

Pending Action Items:
{json.dumps(actions, indent=2) if actions else 'None'}

Generate a briefing in this JSON format:
{{
    "summary": "Brief overview of what user should know going in",
    "participant_insights": [
        {{
            "name": "Participant name",
            "key_insight": "What to remember about them",
            "suggested_topics": ["topic1", "topic2"]
        }}
    ],
    "talking_points": [
        "Suggested talking point 1",
        "Suggested talking point 2"
    ],
    "follow_up_items": [
        "Commitment or action to address in this meeting"
    ],
    "topics_to_avoid": [
        "Topics already covered extensively"
    ],
    "preparation_tips": [
        "Specific preparation suggestions"
    ],
    "questions_to_ask": [
        "Suggested questions for the meeting"
    ]
}}{language_instruction}"""

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
            print(f"Briefing generation error: {e}")
            return {
                "summary": get_fallback_message("unable_to_generate", language),
                "participant_insights": [],
                "talking_points": [],
                "follow_up_items": [],
                "topics_to_avoid": [],
                "preparation_tips": [],
                "questions_to_ask": [],
            }

    async def extract_participants_from_meeting(
        self, meeting_id: int, user_id: int
    ) -> List[ParticipantMemory]:
        """Auto-extract and store participant information from a meeting."""
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.meeting_id == meeting_id)
            .all()
        )

        if not conversations:
            return []

        # Build transcript
        transcript = "\n".join(
            [
                f"{c.speaker or 'Unknown'}: {c.heard_text}"
                for c in conversations
                if c.heard_text
            ]
        )

        # Extract participants with Claude
        prompt = f"""Analyze this meeting transcript and extract information about participants.

Transcript:
{transcript}

For each participant (other than the user), provide:
{{
    "participants": [
        {{
            "name": "Their name",
            "role": "Their apparent role/title",
            "company": "Their company if mentioned",
            "key_points": ["Important things they said/care about"],
            "topics": ["Topics they discussed"]
        }}
    ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content.strip())
            participants = data.get("participants", [])

            stored = []
            for p in participants:
                # Check if already exists
                existing = (
                    self.db.query(ParticipantMemory)
                    .filter(
                        ParticipantMemory.user_id == user_id,
                        ParticipantMemory.participant_name.ilike(p["name"]),
                    )
                    .first()
                )

                if existing:
                    # Update existing
                    existing.interaction_count += 1
                    existing.last_interaction_at = datetime.utcnow()
                    if p.get("key_points"):
                        existing.key_points = list(
                            set((existing.key_points or []) + p["key_points"])
                        )
                    if p.get("topics"):
                        existing.topics_discussed = list(
                            set((existing.topics_discussed or []) + p["topics"])
                        )
                    stored.append(existing)
                else:
                    # Create new
                    memory = ParticipantMemory(
                        user_id=user_id,
                        participant_name=p["name"],
                        participant_role=p.get("role"),
                        company=p.get("company"),
                        key_points=p.get("key_points", []),
                        topics_discussed=p.get("topics", []),
                        interaction_count=1,
                        last_interaction_at=datetime.utcnow(),
                    )
                    self.db.add(memory)
                    stored.append(memory)

            self.db.commit()
            return stored

        except Exception as e:
            print(f"Participant extraction error: {e}")
            return []

    async def get_variety_suggestions(
        self, user_id: int, topic: str, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """For TV/media appearances, suggest points not yet covered."""
        # Get user's preferred language if not specified
        if language is None:
            user = self.db.query(User).filter(User.id == user_id).first()
            language = getattr(user, 'preferred_language', 'en') or 'en' if user else 'en'

        # Get user's media appearances on this topic
        from models import MediaAppearance

        appearances = (
            self.db.query(MediaAppearance)
            .filter(
                MediaAppearance.user_id == user_id,
                MediaAppearance.topic.ilike(f"%{topic}%"),
            )
            .order_by(MediaAppearance.created_at.desc())
            .limit(10)
            .all()
        )

        # Collect all points already made
        points_made = []
        for app in appearances:
            if app.points_made:
                points_made.extend(app.points_made)

        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        # Generate new suggestions
        prompt = f"""For a TV/media appearance about "{topic}", suggest fresh talking points.

Points already made in previous appearances:
{json.dumps(points_made) if points_made else 'None - this is a new topic'}

Generate unique, fresh talking points that:
1. Don't repeat previous points
2. Offer new perspectives
3. Are memorable and quotable

Return as JSON:
{{
    "fresh_points": [
        "New talking point 1",
        "New talking point 2",
        "New talking point 3"
    ],
    "angles_to_explore": [
        "New angle 1",
        "New angle 2"
    ],
    "avoid_repeating": [
        "Point already overused"
    ]
}}{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content.strip())

        except Exception as e:
            print(f"Variety suggestions error: {e}")
            return {
                "fresh_points": [],
                "angles_to_explore": [],
                "avoid_repeating": points_made[:5] if points_made else [],
            }
