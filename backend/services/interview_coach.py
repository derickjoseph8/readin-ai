"""Interview Coaching Service for job interview improvement."""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    JobApplication,
    Interview,
    Meeting,
    Conversation,
    User,
    UserLearningProfile,
)
from services.language_service import get_localized_prompt_suffix, get_fallback_message


class InterviewCoach:
    """ML-powered interview coaching and improvement suggestions."""

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv(
            "SUMMARY_GENERATION_MODEL", "claude-sonnet-4-20250514"
        )

    async def analyze_interview(self, interview_id: int, language: Optional[str] = None) -> Dict[str, Any]:
        """Analyze an interview and provide improvement suggestions."""
        interview = (
            self.db.query(Interview).filter(Interview.id == interview_id).first()
        )

        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        # Get user's preferred language if not specified
        job = (
            self.db.query(JobApplication)
            .filter(JobApplication.id == interview.job_application_id)
            .first()
        )
        if language is None and job:
            user = self.db.query(User).filter(User.id == job.user_id).first()
            language = getattr(user, 'preferred_language', 'en') or 'en' if user else 'en'
        elif language is None:
            language = 'en'

        # Get linked meeting conversations
        conversations = []
        if interview.meeting_id:
            conversations = (
                self.db.query(Conversation)
                .filter(Conversation.meeting_id == interview.meeting_id)
                .order_by(Conversation.created_at)
                .all()
            )

        # Build transcript
        transcript = self._build_transcript(conversations)

        # Analyze with Claude
        analysis = await self._analyze_with_claude(
            transcript=transcript,
            interview_type=interview.interview_type,
            company=job.company if job else None,
            position=job.position if job else None,
            language=language,
        )

        # Update interview with analysis
        interview.performance_score = analysis.get("overall_score")
        interview.improvement_notes = analysis.get("improvements", [])
        interview.analyzed_at = datetime.utcnow()
        self.db.commit()

        return analysis

    def _build_transcript(self, conversations: List[Conversation]) -> str:
        """Build transcript from conversations."""
        if not conversations:
            return "No transcript available"

        lines = []
        for conv in conversations:
            if conv.heard_text:
                lines.append(f"Interviewer: {conv.heard_text}")
            if conv.response_text:
                lines.append(f"Candidate: {conv.response_text}")
        return "\n".join(lines)

    async def _analyze_with_claude(
        self,
        transcript: str,
        interview_type: Optional[str],
        company: Optional[str],
        position: Optional[str],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Analyze interview with Claude."""
        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Analyze this job interview transcript and provide detailed feedback.

Company: {company or 'Unknown'}
Position: {position or 'Unknown'}
Interview Type: {interview_type or 'General'}

Transcript:
{transcript}

Provide comprehensive analysis in this JSON format:
{{
    "overall_score": 1-10,
    "summary": "Brief overall assessment",
    "strengths": [
        {{
            "area": "What they did well",
            "example": "Specific example from transcript",
            "impact": "Why this was effective"
        }}
    ],
    "improvements": [
        {{
            "area": "Area needing improvement",
            "issue": "What was problematic",
            "suggestion": "Specific improvement suggestion",
            "example_response": "How they could have answered better"
        }}
    ],
    "question_handling": {{
        "behavioral": {{
            "score": 1-10,
            "feedback": "How well they handled behavioral questions"
        }},
        "technical": {{
            "score": 1-10,
            "feedback": "How well they handled technical questions"
        }},
        "situational": {{
            "score": 1-10,
            "feedback": "How well they handled situational questions"
        }}
    }},
    "communication_style": {{
        "clarity": 1-10,
        "confidence": 1-10,
        "professionalism": 1-10,
        "engagement": 1-10
    }},
    "red_flags": [
        "Any concerning patterns or responses"
    ],
    "next_steps": [
        "Specific preparation recommendations for next interview"
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
            print(f"Interview analysis error: {e}")
            return {
                "overall_score": 5,
                "summary": get_fallback_message("unable_to_generate", language),
                "strengths": [],
                "improvements": [],
                "question_handling": {},
                "communication_style": {},
                "red_flags": [],
                "next_steps": [],
            }

    async def get_improvement_plan(self, user_id: int, language: Optional[str] = None) -> Dict[str, Any]:
        """Generate personalized interview improvement plan based on history."""
        # Get user's preferred language if not specified
        if language is None:
            user = self.db.query(User).filter(User.id == user_id).first()
            language = getattr(user, 'preferred_language', 'en') or 'en' if user else 'en'

        # Get all analyzed interviews
        interviews = (
            self.db.query(Interview)
            .join(JobApplication)
            .filter(
                JobApplication.user_id == user_id,
                Interview.performance_score.isnot(None),
            )
            .order_by(Interview.interview_date.desc())
            .limit(10)
            .all()
        )

        if not interviews:
            return {
                "status": "insufficient_data",
                "message": get_fallback_message("no_data", language),
            }

        # Aggregate improvement notes
        all_improvements = []
        scores = []
        for interview in interviews:
            if interview.improvement_notes:
                all_improvements.extend(interview.improvement_notes)
            if interview.performance_score:
                scores.append(interview.performance_score)

        avg_score = sum(scores) / len(scores) if scores else 0

        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        # Generate improvement plan with Claude
        prompt = f"""Based on feedback from {len(interviews)} job interviews, create a personalized improvement plan.

Average Performance Score: {avg_score:.1f}/10
Recent Scores: {scores}

Improvement Notes from Interviews:
{json.dumps(all_improvements, indent=2)}

Create a prioritized improvement plan in this JSON format:
{{
    "current_level": "beginner/intermediate/advanced",
    "average_score": {avg_score:.1f},
    "trend": "improving/declining/stable",
    "priority_improvements": [
        {{
            "area": "Most important area to work on",
            "frequency": "How often this issue appeared",
            "action_plan": "Specific steps to improve",
            "practice_exercises": ["exercise 1", "exercise 2"]
        }}
    ],
    "strengths_to_leverage": [
        "Strength to emphasize"
    ],
    "weekly_goals": [
        "Specific goal for this week"
    ],
    "resources": [
        {{
            "type": "book/video/practice",
            "title": "Resource name",
            "description": "How it helps"
        }}
    ],
    "mock_interview_focus": [
        "Topic to practice in mock interviews"
    ]
}}{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content.strip())

        except Exception as e:
            print(f"Improvement plan error: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def polish_response(
        self, original_response: str, question_type: str, user_id: int, language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Polish and improve a candidate's response."""
        # Get user's profession for context
        user = self.db.query(User).filter(User.id == user_id).first()
        profession_context = ""
        if user and user.profession:
            profession_context = f"The candidate is a {user.profession.name}."

        # Get user's preferred language if not specified
        if language is None and user:
            language = getattr(user, 'preferred_language', 'en') or 'en'
        elif language is None:
            language = 'en'

        # Get user's learning profile
        profile = (
            self.db.query(UserLearningProfile)
            .filter(UserLearningProfile.user_id == user_id)
            .first()
        )

        style_notes = ""
        if profile:
            if profile.formality_level and profile.formality_level > 0.7:
                style_notes = "Maintain a formal, professional tone."
            elif profile.formality_level and profile.formality_level < 0.3:
                style_notes = "Keep a conversational but professional tone."

        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Improve this interview response while maintaining the candidate's voice.

Question Type: {question_type}
{profession_context}
{style_notes}

Original Response:
{original_response}

Provide improvements in this JSON format:
{{
    "polished_response": "The improved response",
    "key_changes": [
        "What was changed and why"
    ],
    "structure_used": "STAR/CAR/etc if applicable",
    "strength_highlights": [
        "Strengths emphasized in the polished version"
    ],
    "tips": [
        "Tips for delivering this response"
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
            print(f"Response polishing error: {e}")
            return {
                "polished_response": original_response,
                "key_changes": [],
                "tips": [get_fallback_message("unable_to_generate", language)],
            }

    async def get_common_questions(
        self, position: str, company: Optional[str] = None, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Get common interview questions for a position."""
        # Get language-specific prompt suffix
        language_instruction = get_localized_prompt_suffix(language)

        prompt = f"""Generate common interview questions for this role:

Position: {position}
Company: {company or 'General'}

Provide questions in this JSON format:
{{
    "questions": [
        {{
            "question": "The interview question",
            "type": "behavioral/technical/situational/general",
            "difficulty": "easy/medium/hard",
            "what_they_assess": "What interviewer is looking for",
            "sample_answer_structure": "How to structure a good answer"
        }}
    ]
}}

Include 10 questions across different types.{language_instruction}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content.strip())
            return data.get("questions", [])

        except Exception as e:
            print(f"Question generation error: {e}")
            return []

    async def get_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get interview performance analytics for user."""
        # Get all interviews
        interviews = (
            self.db.query(Interview)
            .join(JobApplication)
            .filter(JobApplication.user_id == user_id)
            .all()
        )

        # Get applications
        applications = (
            self.db.query(JobApplication)
            .filter(JobApplication.user_id == user_id)
            .all()
        )

        # Calculate stats
        total_applications = len(applications)
        total_interviews = len(interviews)

        scores = [i.performance_score for i in interviews if i.performance_score]
        avg_score = sum(scores) / len(scores) if scores else 0

        # Status breakdown
        status_counts = {}
        for app in applications:
            status_counts[app.status] = status_counts.get(app.status, 0) + 1

        # Interview type breakdown
        type_counts = {}
        type_scores = {}
        for interview in interviews:
            itype = interview.interview_type or "general"
            type_counts[itype] = type_counts.get(itype, 0) + 1
            if interview.performance_score:
                if itype not in type_scores:
                    type_scores[itype] = []
                type_scores[itype].append(interview.performance_score)

        type_averages = {
            k: sum(v) / len(v) for k, v in type_scores.items() if v
        }

        # Score trend
        recent_scores = [
            i.performance_score
            for i in sorted(interviews, key=lambda x: x.interview_date or datetime.min)[-5:]
            if i.performance_score
        ]

        trend = "stable"
        if len(recent_scores) >= 3:
            if recent_scores[-1] > recent_scores[0]:
                trend = "improving"
            elif recent_scores[-1] < recent_scores[0]:
                trend = "declining"

        return {
            "total_applications": total_applications,
            "total_interviews": total_interviews,
            "average_score": round(avg_score, 1),
            "score_trend": trend,
            "recent_scores": recent_scores,
            "application_status": status_counts,
            "interviews_by_type": type_counts,
            "average_by_type": type_averages,
            "success_rate": (
                status_counts.get("offer", 0) / total_applications
                if total_applications > 0
                else 0
            ),
        }
