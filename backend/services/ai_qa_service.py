"""
AI-Powered Quality Assurance Service for Chat Sessions.

Uses Claude AI to analyze chat transcripts and provide:
- Automated quality scoring
- Response quality analysis
- Professionalism assessment
- Resolution effectiveness evaluation
- Agent performance insights
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    ChatSession, ChatMessage, ChatQARecord, User, TeamMember, SupportTeam
)

logger = logging.getLogger(__name__)


class AIQAService:
    """
    Service for AI-powered quality assurance of chat sessions.
    """

    def __init__(self, db: Session):
        self.db = db
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not configured. AI QA features disabled.")

    def is_available(self) -> bool:
        """Check if AI QA service is available."""
        return self.client is not None

    async def analyze_session(
        self,
        session_id: int,
        reviewer_id: int
    ) -> Optional[ChatQARecord]:
        """
        Analyze a chat session using AI and create a QA record.

        Args:
            session_id: ID of the chat session to analyze
            reviewer_id: ID of the user requesting the analysis (for audit)

        Returns:
            ChatQARecord with AI-generated scores and analysis
        """
        if not self.client:
            logger.error("AI QA service not available - no API key")
            return None

        # Get session with messages
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            logger.error(f"Session {session_id} not found")
            return None

        # Check if already reviewed
        existing = self.db.query(ChatQARecord).filter(
            ChatQARecord.session_id == session_id
        ).first()
        if existing:
            logger.warning(f"Session {session_id} already has a QA review")
            return existing

        # Get messages
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()

        if not messages:
            logger.warning(f"No messages found for session {session_id}")
            return None

        # Build transcript
        transcript = self._build_transcript(session, messages)

        # Get AI analysis
        analysis = await self._get_ai_analysis(transcript, session)

        if not analysis:
            logger.error(f"Failed to get AI analysis for session {session_id}")
            return None

        # Create QA record
        qa_record = ChatQARecord(
            session_id=session_id,
            reviewer_id=reviewer_id,
            overall_score=analysis.get("overall_score", 3),
            response_time_score=analysis.get("response_time_score"),
            resolution_score=analysis.get("resolution_score"),
            professionalism_score=analysis.get("professionalism_score"),
            notes=analysis.get("summary", "AI-generated review"),
            tags=analysis.get("tags", []),
            is_ai_review=True,
            ai_analysis=analysis,
            ai_confidence=analysis.get("confidence", 0.8)
        )

        self.db.add(qa_record)
        self.db.commit()
        self.db.refresh(qa_record)

        return qa_record

    def _build_transcript(
        self,
        session: ChatSession,
        messages: List[ChatMessage]
    ) -> str:
        """Build a formatted transcript for AI analysis."""
        # Get user info
        user = self.db.query(User).filter(User.id == session.user_id).first()
        user_name = user.full_name if user else "Customer"

        # Get agent info
        agent_name = "AI Bot (Novah)"
        if session.agent_id:
            member = self.db.query(TeamMember).filter(
                TeamMember.id == session.agent_id
            ).first()
            if member:
                agent_user = self.db.query(User).filter(
                    User.id == member.user_id
                ).first()
                if agent_user:
                    agent_name = agent_user.full_name

        # Format transcript
        lines = [
            f"=== Chat Session Transcript ===",
            f"Session ID: {session.id}",
            f"Customer: {user_name}",
            f"Agent: {agent_name}",
            f"Started: {session.started_at}",
            f"Ended: {session.ended_at or 'Ongoing'}",
            f"AI Handled: {session.is_ai_handled}",
            f"Resolution Status: {session.ai_resolution_status or 'Unknown'}",
            f"",
            "=== Messages ===",
            ""
        ]

        for msg in messages:
            sender = "Customer" if msg.sender_type == "customer" else (
                "Novah (AI)" if msg.sender_type == "bot" else "Agent"
            )
            timestamp = msg.created_at.strftime("%H:%M:%S") if msg.created_at else ""
            lines.append(f"[{timestamp}] {sender}: {msg.message}")

        return "\n".join(lines)

    async def _get_ai_analysis(
        self,
        transcript: str,
        session: ChatSession
    ) -> Optional[Dict[str, Any]]:
        """Get AI analysis of the chat transcript."""
        try:
            system_prompt = """You are a Quality Assurance analyst for a customer support chat system.
Your task is to analyze chat transcripts and provide detailed quality assessments.

Evaluate each chat on these criteria (score 1-5):
1. Overall Quality: General effectiveness of the support interaction
2. Response Time: How promptly responses were provided
3. Resolution: How well the issue was resolved
4. Professionalism: Courtesy, clarity, and professional conduct

Also identify:
- Key strengths and weaknesses
- Specific improvement suggestions
- Relevant tags (e.g., "escalated", "resolved_first_contact", "needs_training", "excellent_service")

Respond ONLY with a valid JSON object in this exact format:
{
    "overall_score": <1-5>,
    "response_time_score": <1-5>,
    "resolution_score": <1-5>,
    "professionalism_score": <1-5>,
    "confidence": <0.0-1.0>,
    "summary": "<brief 2-3 sentence summary>",
    "strengths": ["<strength1>", "<strength2>"],
    "weaknesses": ["<weakness1>", "<weakness2>"],
    "suggestions": ["<suggestion1>", "<suggestion2>"],
    "tags": ["<tag1>", "<tag2>"],
    "agent_feedback": "<specific feedback for the agent>"
}"""

            user_message = f"""Please analyze this customer support chat transcript and provide a quality assessment:

{transcript}

Respond with ONLY a valid JSON object, no additional text."""

            response = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost-efficiency
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Parse the response
            content = response.content[0].text.strip()

            # Try to extract JSON from the response
            if content.startswith("{"):
                analysis = json.loads(content)
            else:
                # Try to find JSON in the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    logger.error(f"Could not parse AI response: {content[:200]}")
                    return None

            # Validate and clamp scores
            for key in ["overall_score", "response_time_score", "resolution_score", "professionalism_score"]:
                if key in analysis:
                    analysis[key] = max(1, min(5, int(analysis[key])))

            if "confidence" in analysis:
                analysis["confidence"] = max(0.0, min(1.0, float(analysis["confidence"])))

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return None

    async def batch_analyze(
        self,
        reviewer_id: int,
        limit: int = 10,
        min_messages: int = 3
    ) -> Dict[str, Any]:
        """
        Analyze multiple unreviewed sessions in batch.

        Args:
            reviewer_id: ID of user requesting the analysis
            limit: Maximum sessions to analyze
            min_messages: Minimum messages required for analysis

        Returns:
            Summary of batch analysis results
        """
        if not self.client:
            return {"error": "AI QA service not available"}

        # Find unreviewed, ended sessions
        reviewed_ids = self.db.query(ChatQARecord.session_id).subquery()

        sessions = self.db.query(ChatSession).filter(
            ChatSession.status == "ended",
            ~ChatSession.id.in_(reviewed_ids)
        ).order_by(ChatSession.ended_at.desc()).limit(limit * 2).all()

        # Filter by message count
        eligible_sessions = []
        for session in sessions:
            msg_count = self.db.query(func.count(ChatMessage.id)).filter(
                ChatMessage.session_id == session.id
            ).scalar()
            if msg_count >= min_messages:
                eligible_sessions.append(session)
            if len(eligible_sessions) >= limit:
                break

        results = {
            "analyzed": 0,
            "failed": 0,
            "skipped": 0,
            "sessions": []
        }

        for session in eligible_sessions:
            try:
                record = await self.analyze_session(session.id, reviewer_id)
                if record:
                    results["analyzed"] += 1
                    results["sessions"].append({
                        "session_id": session.id,
                        "score": record.overall_score
                    })
                else:
                    results["failed"] += 1
            except Exception as e:
                logger.error(f"Error analyzing session {session.id}: {e}")
                results["failed"] += 1

        return results

    def get_agent_ratings(
        self,
        agent_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated agent ratings from AI and human reviews.

        Args:
            agent_id: Filter by specific agent (optional)
            days: Number of days to include

        Returns:
            List of agent ratings with breakdown
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get sessions with reviews
        query = self.db.query(
            ChatSession.agent_id,
            func.count(ChatQARecord.id).label("total_reviews"),
            func.avg(ChatQARecord.overall_score).label("avg_overall"),
            func.avg(ChatQARecord.response_time_score).label("avg_response_time"),
            func.avg(ChatQARecord.resolution_score).label("avg_resolution"),
            func.avg(ChatQARecord.professionalism_score).label("avg_professionalism"),
            func.sum(ChatQARecord.is_ai_review.cast(Integer)).label("ai_reviews"),
        ).join(
            ChatQARecord, ChatSession.id == ChatQARecord.session_id
        ).filter(
            ChatSession.agent_id.isnot(None),
            ChatQARecord.reviewed_at >= start_date
        ).group_by(ChatSession.agent_id)

        if agent_id:
            query = query.filter(ChatSession.agent_id == agent_id)

        results = query.all()

        ratings = []
        for row in results:
            # Get agent info
            member = self.db.query(TeamMember).filter(
                TeamMember.id == row.agent_id
            ).first()
            agent_name = "Unknown"
            if member:
                agent_user = self.db.query(User).filter(
                    User.id == member.user_id
                ).first()
                if agent_user:
                    agent_name = agent_user.full_name

            ratings.append({
                "agent_id": row.agent_id,
                "agent_name": agent_name,
                "total_reviews": row.total_reviews,
                "ai_reviews": row.ai_reviews or 0,
                "human_reviews": row.total_reviews - (row.ai_reviews or 0),
                "avg_overall": round(row.avg_overall or 0, 2),
                "avg_response_time": round(row.avg_response_time or 0, 2),
                "avg_resolution": round(row.avg_resolution or 0, 2),
                "avg_professionalism": round(row.avg_professionalism or 0, 2),
            })

        return sorted(ratings, key=lambda x: x["avg_overall"], reverse=True)


# Import for Integer cast
from sqlalchemy import Integer
