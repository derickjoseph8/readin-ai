"""
AI-Powered Meeting Recommendations Service.

Provides:
- Next steps suggestions based on meeting content
- Meeting preparation hints
- Participant insights across meetings
- Topic suggestions from meeting history
- Risk detection from meeting content

Uses Claude AI for intelligent analysis and recommendations.
"""

import os
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from models import (
    Meeting,
    Conversation,
    MeetingSummary,
    ActionItem,
    Commitment,
    User,
    ParticipantMemory,
    Topic,
)
from services.cache_service import cache, CacheKeys, CacheTTL
from services.language_service import get_localized_prompt_suffix, get_fallback_message

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    AI-powered recommendation service for meetings.

    Leverages Claude to analyze meeting content and generate
    actionable insights, next steps, and risk assessments.
    """

    # Cache TTLs for different recommendation types
    CACHE_TTL_NEXT_STEPS = CacheTTL.MEDIUM  # 5 minutes
    CACHE_TTL_MEETING_PREP = CacheTTL.LONG  # 15 minutes
    CACHE_TTL_PARTICIPANT_INSIGHTS = CacheTTL.LONG  # 15 minutes
    CACHE_TTL_TOPIC_SUGGESTIONS = CacheTTL.VERY_LONG  # 1 hour
    CACHE_TTL_RISKS = CacheTTL.MEDIUM  # 5 minutes

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv(
            "RECOMMENDATION_MODEL",
            os.getenv("SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514")
        )

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments."""
        key_data = ":".join(str(arg) for arg in args)
        return f"recommendation:{prefix}:{key_data}"

    def _get_user_language(self, user_id: int) -> str:
        """Get user's preferred language."""
        user = self.db.query(User).filter(User.id == user_id).first()
        return getattr(user, 'preferred_language', 'en') or 'en' if user else 'en'

    def _get_meeting_transcript(self, meeting_id: int) -> str:
        """Build transcript from meeting conversations."""
        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.meeting_id == meeting_id)
            .order_by(Conversation.timestamp)
            .all()
        )

        if not conversations:
            return ""

        lines = []
        for conv in conversations:
            time_str = conv.timestamp.strftime("%H:%M") if conv.timestamp else ""
            speaker = conv.speaker or "Unknown"
            lines.append(f"[{time_str}] {speaker}: {conv.heard_text}")
            if conv.response_text:
                lines.append(f"[{time_str}] AI Response: {conv.response_text}")
        return "\n".join(lines)

    def _get_meeting_context(self, meeting_id: int) -> Dict[str, Any]:
        """Get comprehensive meeting context for AI analysis."""
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {}

        # Get summary if available
        summary = (
            self.db.query(MeetingSummary)
            .filter(MeetingSummary.meeting_id == meeting_id)
            .first()
        )

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

        return {
            "meeting_id": meeting.id,
            "meeting_type": meeting.meeting_type,
            "title": meeting.title,
            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
            "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
            "duration_seconds": meeting.duration_seconds,
            "participant_count": meeting.participant_count,
            "status": meeting.status,
            "notes": meeting.notes,
            "summary": {
                "text": summary.summary_text if summary else None,
                "key_points": summary.key_points if summary else [],
                "sentiment": summary.sentiment if summary else None,
                "topics_discussed": summary.topics_discussed if summary else [],
                "decisions_made": summary.decisions_made if summary else [],
            },
            "action_items": [
                {
                    "assignee": ai.assignee,
                    "description": ai.description,
                    "due_date": ai.due_date.isoformat() if ai.due_date else None,
                    "priority": ai.priority,
                    "status": ai.status,
                }
                for ai in action_items
            ],
            "commitments": [
                {
                    "description": c.description,
                    "due_date": c.due_date.isoformat() if c.due_date else None,
                    "status": c.status,
                }
                for c in commitments
            ],
        }

    async def get_next_steps(
        self,
        meeting_id: int,
        max_steps: int = 5,
        language: Optional[str] = None,
    ) -> List[str]:
        """
        Suggest actionable next steps based on meeting content.

        Analyzes the meeting transcript, summary, and action items
        to generate prioritized next steps for the user.

        Args:
            meeting_id: The meeting to analyze
            max_steps: Maximum number of steps to suggest
            language: Language for response (uses user preference if not set)

        Returns:
            List of recommended next steps
        """
        # Check cache
        cache_key = self._get_cache_key("next_steps", meeting_id, max_steps)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Get meeting and verify ownership
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return []

        # Get language preference
        if language is None:
            language = self._get_user_language(meeting.user_id)

        # Get meeting context
        context = self._get_meeting_context(meeting_id)
        transcript = self._get_meeting_transcript(meeting_id)

        if not context and not transcript:
            return []

        # Generate next steps with Claude
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Based on this meeting, suggest {max_steps} specific, actionable next steps.

Meeting Context:
{json.dumps(context, indent=2)}

Meeting Transcript (excerpt):
{transcript[:3000] if transcript else 'No transcript available'}

Consider:
1. Action items already identified
2. Commitments made
3. Decisions that need follow-up
4. Open questions or concerns raised
5. Deadlines mentioned

Return a JSON array of {max_steps} specific, actionable next steps.
Each step should be concrete and immediately actionable.
Order by priority (most important first).

Format: ["Step 1", "Step 2", ...]{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            steps = json.loads(content.strip())

            # Cache the result
            cache.set(cache_key, steps, self.CACHE_TTL_NEXT_STEPS)

            return steps[:max_steps]

        except Exception as e:
            logger.error(f"Failed to generate next steps for meeting {meeting_id}: {e}")
            return []

    async def get_meeting_prep(
        self,
        meeting_id: int,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate preparation hints for an upcoming meeting.

        Analyzes past meetings with similar participants, topics,
        and meeting type to provide preparation guidance.

        Args:
            meeting_id: The meeting to prepare for
            language: Language for response (uses user preference if not set)

        Returns:
            Dictionary with preparation hints including:
            - key_topics: Topics to review
            - suggested_agenda: Recommended agenda items
            - participant_notes: Notes about participants
            - questions_to_consider: Questions to think about
            - documents_to_review: Relevant past materials
            - talking_points: Suggested talking points
        """
        # Check cache
        cache_key = self._get_cache_key("meeting_prep", meeting_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {}

        if language is None:
            language = self._get_user_language(meeting.user_id)

        # Get user's recent meetings of same type
        recent_similar = (
            self.db.query(Meeting)
            .filter(
                Meeting.user_id == meeting.user_id,
                Meeting.meeting_type == meeting.meeting_type,
                Meeting.id != meeting_id,
                Meeting.status == "ended",
            )
            .order_by(desc(Meeting.started_at))
            .limit(5)
            .all()
        )

        # Get summaries from recent similar meetings
        recent_summaries = []
        for m in recent_similar:
            summary = (
                self.db.query(MeetingSummary)
                .filter(MeetingSummary.meeting_id == m.id)
                .first()
            )
            if summary:
                recent_summaries.append({
                    "meeting_title": m.title,
                    "date": m.started_at.isoformat() if m.started_at else None,
                    "key_points": summary.key_points or [],
                    "topics": summary.topics_discussed or [],
                    "decisions": summary.decisions_made or [],
                })

        # Get pending commitments for user
        pending_commitments = (
            self.db.query(Commitment)
            .filter(
                Commitment.user_id == meeting.user_id,
                Commitment.status == "pending",
            )
            .order_by(Commitment.due_date.asc().nullslast())
            .limit(10)
            .all()
        )

        # Get pending action items
        pending_actions = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.user_id == meeting.user_id,
                ActionItem.status.in_(["pending", "in_progress"]),
            )
            .order_by(ActionItem.due_date.asc().nullslast())
            .limit(10)
            .all()
        )

        # Get user's top topics
        user_topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == meeting.user_id)
            .order_by(desc(Topic.frequency))
            .limit(10)
            .all()
        )

        # Generate prep hints with Claude
        language_instruction = get_localized_prompt_suffix(language)

        context = {
            "meeting_type": meeting.meeting_type,
            "meeting_title": meeting.title,
            "notes": meeting.notes,
            "recent_similar_meetings": recent_summaries,
            "pending_commitments": [
                {"description": c.description, "due_date": c.due_date.isoformat() if c.due_date else None}
                for c in pending_commitments
            ],
            "pending_actions": [
                {"description": a.description, "priority": a.priority, "due_date": a.due_date.isoformat() if a.due_date else None}
                for a in pending_actions
            ],
            "frequent_topics": [t.name for t in user_topics],
        }

        prompt = f"""Generate comprehensive meeting preparation hints based on this context.

Meeting to prepare for:
- Type: {meeting.meeting_type}
- Title: {meeting.title or 'Not specified'}
- Notes: {meeting.notes or 'None'}

Context:
{json.dumps(context, indent=2)}

Generate preparation hints in this JSON format:
{{
    "key_topics": ["Topic 1 to review", "Topic 2 to review"],
    "suggested_agenda": ["Agenda item 1", "Agenda item 2"],
    "participant_notes": ["Note about participant relationship", "Previous discussion point"],
    "questions_to_consider": ["Question 1?", "Question 2?"],
    "documents_to_review": ["Document or past meeting to review"],
    "talking_points": ["Key point to make", "Important topic to raise"],
    "follow_up_items": ["Commitment to address", "Action item to discuss"],
    "preparation_tips": ["Specific tip for this meeting type"]
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

            prep_hints = json.loads(content.strip())
            prep_hints["meeting_id"] = meeting_id
            prep_hints["generated_at"] = datetime.utcnow().isoformat()

            # Cache the result
            cache.set(cache_key, prep_hints, self.CACHE_TTL_MEETING_PREP)

            return prep_hints

        except Exception as e:
            logger.error(f"Failed to generate meeting prep for meeting {meeting_id}: {e}")
            return {
                "meeting_id": meeting_id,
                "key_topics": [],
                "suggested_agenda": [],
                "participant_notes": [],
                "questions_to_consider": [],
                "documents_to_review": [],
                "talking_points": [],
                "follow_up_items": [],
                "preparation_tips": [],
                "error": "Failed to generate preparation hints",
            }

    async def get_participant_insights(
        self,
        participant_id: int,
        user_id: int,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get AI-powered insights about a participant across meetings.

        Analyzes all interactions with a participant to provide
        communication insights and relationship guidance.

        Args:
            participant_id: The ParticipantMemory ID
            user_id: The user requesting insights
            language: Language for response

        Returns:
            Dictionary with participant insights
        """
        # Check cache
        cache_key = self._get_cache_key("participant_insights", participant_id, user_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Get participant memory
        participant = (
            self.db.query(ParticipantMemory)
            .filter(
                ParticipantMemory.id == participant_id,
                ParticipantMemory.user_id == user_id,
            )
            .first()
        )

        if not participant:
            return {"error": "Participant not found"}

        if language is None:
            language = self._get_user_language(user_id)

        # Get meetings involving this participant (by name search in conversations)
        # Note: This is a simplified approach - could be enhanced with participant tracking

        participant_data = {
            "name": participant.participant_name,
            "role": participant.participant_role,
            "company": participant.company,
            "key_points": participant.key_points or [],
            "topics_discussed": participant.topics_discussed or [],
            "communication_style": participant.communication_style,
            "relationship_notes": participant.relationship_notes,
            "meeting_count": participant.meeting_count,
            "last_interaction": participant.last_interaction.isoformat() if participant.last_interaction else None,
            "first_interaction": participant.first_interaction.isoformat() if participant.first_interaction else None,
        }

        # Generate insights with Claude
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Analyze this participant's profile and provide actionable insights for better collaboration.

Participant Profile:
{json.dumps(participant_data, indent=2)}

Generate insights in this JSON format:
{{
    "relationship_summary": "Brief summary of the relationship",
    "communication_recommendations": [
        "How to communicate effectively with this person"
    ],
    "topics_of_interest": [
        "Topics they care about"
    ],
    "conversation_starters": [
        "Good topics to bring up"
    ],
    "things_to_remember": [
        "Important things to keep in mind"
    ],
    "collaboration_tips": [
        "Tips for working together effectively"
    ],
    "potential_opportunities": [
        "Opportunities for deeper collaboration"
    ],
    "relationship_health": "healthy/neutral/needs_attention",
    "next_interaction_suggestions": [
        "Suggestions for next interaction"
    ]
}}{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1536,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            insights = json.loads(content.strip())
            insights["participant_id"] = participant_id
            insights["participant_name"] = participant.participant_name
            insights["generated_at"] = datetime.utcnow().isoformat()

            # Cache the result
            cache.set(cache_key, insights, self.CACHE_TTL_PARTICIPANT_INSIGHTS)

            return insights

        except Exception as e:
            logger.error(f"Failed to generate participant insights for {participant_id}: {e}")
            return {
                "participant_id": participant_id,
                "participant_name": participant.participant_name,
                "error": "Failed to generate insights",
            }

    async def get_topic_suggestions(
        self,
        user_id: int,
        meeting_type: Optional[str] = None,
        limit: int = 10,
        language: Optional[str] = None,
    ) -> List[str]:
        """
        Suggest topics based on user's meeting history.

        Analyzes past meetings, topics discussed, and user's
        expertise areas to suggest relevant topics for future meetings.

        Args:
            user_id: The user to get suggestions for
            meeting_type: Optional filter by meeting type
            limit: Maximum number of suggestions
            language: Language for response

        Returns:
            List of suggested topics
        """
        # Check cache
        cache_key = self._get_cache_key("topic_suggestions", user_id, meeting_type or "all", limit)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        if language is None:
            language = self._get_user_language(user_id)

        # Get user's recent topics
        user_topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id)
            .order_by(desc(Topic.frequency))
            .limit(20)
            .all()
        )

        # Get recent meeting summaries
        query = (
            self.db.query(MeetingSummary)
            .join(Meeting)
            .filter(Meeting.user_id == user_id)
        )
        if meeting_type:
            query = query.filter(Meeting.meeting_type == meeting_type)

        recent_summaries = query.order_by(desc(Meeting.started_at)).limit(10).all()

        # Get pending action items (topics to follow up on)
        pending_actions = (
            self.db.query(ActionItem)
            .filter(
                ActionItem.user_id == user_id,
                ActionItem.status.in_(["pending", "in_progress"]),
            )
            .order_by(ActionItem.due_date.asc().nullslast())
            .limit(10)
            .all()
        )

        context = {
            "frequent_topics": [{"name": t.name, "frequency": t.frequency} for t in user_topics],
            "recent_topics_discussed": [],
            "recent_decisions": [],
            "pending_action_areas": [a.description for a in pending_actions],
            "meeting_type_filter": meeting_type,
        }

        for summary in recent_summaries:
            if summary.topics_discussed:
                context["recent_topics_discussed"].extend(summary.topics_discussed)
            if summary.decisions_made:
                context["recent_decisions"].extend(summary.decisions_made)

        # Generate suggestions with Claude
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Based on this user's meeting history, suggest {limit} relevant topics for future discussions.

Context:
{json.dumps(context, indent=2)}

Consider:
1. Topics they frequently discuss (build on expertise)
2. Topics they haven't covered recently (variety)
3. Follow-ups on recent decisions
4. Areas related to pending action items
5. {"Topics relevant for " + meeting_type + " meetings" if meeting_type else "General relevance"}

Return a JSON array of exactly {limit} topic suggestions.
Each topic should be specific and relevant to professional discussions.

Format: ["Topic 1", "Topic 2", ...]{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            suggestions = json.loads(content.strip())

            # Cache the result
            cache.set(cache_key, suggestions, self.CACHE_TTL_TOPIC_SUGGESTIONS)

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to generate topic suggestions for user {user_id}: {e}")
            return []

    async def detect_risks(
        self,
        meeting_id: int,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Identify potential risks from meeting content.

        Analyzes meeting transcript and summary to identify:
        - Missed deadlines
        - Unclear commitments
        - Potential conflicts
        - Resource concerns
        - Communication issues

        Args:
            meeting_id: The meeting to analyze
            language: Language for response

        Returns:
            List of identified risks with severity and mitigation suggestions
        """
        # Check cache
        cache_key = self._get_cache_key("risks", meeting_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return []

        if language is None:
            language = self._get_user_language(meeting.user_id)

        # Get meeting context and transcript
        context = self._get_meeting_context(meeting_id)
        transcript = self._get_meeting_transcript(meeting_id)

        if not context and not transcript:
            return []

        # Generate risk analysis with Claude
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Analyze this meeting for potential risks and concerns that need attention.

Meeting Context:
{json.dumps(context, indent=2)}

Meeting Transcript (excerpt):
{transcript[:4000] if transcript else 'No transcript available'}

Identify risks in these categories:
1. Deadlines - Unrealistic timelines, missed deadlines mentioned
2. Commitments - Unclear or conflicting commitments
3. Communication - Misunderstandings, unclear expectations
4. Resources - Resource constraints, capacity issues
5. Dependencies - External dependencies, blockers
6. Relationships - Potential conflicts, concerns raised

For each risk found, provide:
- category: The risk category
- title: Short title
- description: Detailed description
- severity: low/medium/high/critical
- evidence: Quote or reference from meeting
- mitigation: Suggested action to address the risk

Return as JSON array:
[
    {{
        "category": "deadlines",
        "title": "Aggressive Q2 timeline",
        "description": "The proposed Q2 deadline may be unrealistic given current team capacity",
        "severity": "high",
        "evidence": "John mentioned concern about the April deadline",
        "mitigation": "Review timeline with stakeholders and identify potential scope reductions"
    }}
]

If no significant risks are identified, return an empty array [].{language_instruction}"""

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

            risks = json.loads(content.strip())

            # Add metadata
            for risk in risks:
                risk["meeting_id"] = meeting_id
                risk["detected_at"] = datetime.utcnow().isoformat()

            # Cache the result
            cache.set(cache_key, risks, self.CACHE_TTL_RISKS)

            return risks

        except Exception as e:
            logger.error(f"Failed to detect risks for meeting {meeting_id}: {e}")
            return []

    async def get_meeting_recommendations(
        self,
        meeting_id: int,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive recommendations for a meeting.

        Combines next steps, risks, and follow-up suggestions
        into a single comprehensive recommendation report.

        Args:
            meeting_id: The meeting to analyze
            language: Language for response

        Returns:
            Dictionary with all recommendations
        """
        # Check cache for combined recommendations
        cache_key = self._get_cache_key("full_recommendations", meeting_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {"error": "Meeting not found"}

        # Get individual recommendations (leveraging their individual caches)
        next_steps = await self.get_next_steps(meeting_id, language=language)
        risks = await self.detect_risks(meeting_id, language=language)

        # Get meeting context
        context = self._get_meeting_context(meeting_id)

        result = {
            "meeting_id": meeting_id,
            "meeting_title": meeting.title,
            "meeting_type": meeting.meeting_type,
            "next_steps": next_steps,
            "risks": risks,
            "action_items": context.get("action_items", []),
            "commitments": context.get("commitments", []),
            "summary": context.get("summary", {}),
            "generated_at": datetime.utcnow().isoformat(),
            "has_urgent_items": any(
                ai.get("priority") == "high" or ai.get("priority") == "urgent"
                for ai in context.get("action_items", [])
            ),
            "has_high_risks": any(
                r.get("severity") in ["high", "critical"]
                for r in risks
            ),
        }

        # Cache combined result
        cache.set(cache_key, result, CacheTTL.MEDIUM)

        return result

    def invalidate_meeting_cache(self, meeting_id: int):
        """Invalidate all cached recommendations for a meeting."""
        patterns = [
            self._get_cache_key("next_steps", meeting_id, "*"),
            self._get_cache_key("meeting_prep", meeting_id),
            self._get_cache_key("risks", meeting_id),
            self._get_cache_key("full_recommendations", meeting_id),
        ]
        for pattern in patterns:
            cache.delete_pattern(pattern.replace("*", ""))

    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cached recommendations for a user."""
        cache.delete_pattern(f"recommendation:topic_suggestions:{user_id}:*")
        cache.delete_pattern(f"recommendation:participant_insights:*:{user_id}")
