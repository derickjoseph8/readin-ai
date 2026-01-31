"""Pattern Analyzer Service for user communication patterns."""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Conversation, UserLearningProfile, Meeting, User


class PatternAnalyzer:
    """Analyze user communication patterns using ML."""

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("TOPIC_EXTRACTION_MODEL", "claude-3-haiku-20240307")

    async def analyze_user_patterns(
        self, user_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """Analyze user's communication patterns from recent conversations."""
        since = datetime.utcnow() - timedelta(days=days)

        # Get recent conversations
        conversations = (
            self.db.query(Conversation)
            .join(Meeting)
            .filter(
                Meeting.user_id == user_id,
                Conversation.created_at >= since,
            )
            .order_by(Conversation.created_at.desc())
            .limit(100)
            .all()
        )

        if not conversations:
            return self._empty_pattern()

        # Prepare conversation samples for analysis
        samples = []
        for conv in conversations[:50]:  # Limit for API
            samples.append(
                {
                    "input": conv.heard_text[:500] if conv.heard_text else "",
                    "response": conv.response_text[:500] if conv.response_text else "",
                }
            )

        return await self._analyze_with_claude(samples, user_id)

    async def _analyze_with_claude(
        self, samples: List[Dict], user_id: int
    ) -> Dict[str, Any]:
        """Use Claude to analyze communication patterns."""
        prompt = f"""Analyze these conversation samples and identify the user's communication patterns.

Samples:
{json.dumps(samples, indent=2)}

Provide analysis in this JSON format:
{{
    "formality_level": 0.0-1.0 (0=casual, 1=formal),
    "verbosity": 0.0-1.0 (0=concise, 1=detailed),
    "technical_depth": 0.0-1.0 (0=simple, 1=technical),
    "preferred_response_length": number (avg words),
    "communication_style": "string describing their style",
    "strengths": ["list", "of", "strengths"],
    "areas_for_improvement": ["list", "of", "areas"],
    "go_to_phrases": ["phrases", "they", "use", "often"],
    "filler_words": ["common", "filler", "words"],
    "tone": "professional/friendly/assertive/etc"
}}"""

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

            return json.loads(content.strip())

        except Exception as e:
            print(f"Pattern analysis error: {e}")
            return self._empty_pattern()

    def _empty_pattern(self) -> Dict[str, Any]:
        """Return empty pattern structure."""
        return {
            "formality_level": 0.5,
            "verbosity": 0.5,
            "technical_depth": 0.5,
            "preferred_response_length": 50,
            "communication_style": "neutral",
            "strengths": [],
            "areas_for_improvement": [],
            "go_to_phrases": [],
            "filler_words": [],
            "tone": "professional",
        }

    async def update_learning_profile(self, user_id: int) -> UserLearningProfile:
        """Update user's learning profile with analyzed patterns."""
        patterns = await self.analyze_user_patterns(user_id)

        profile = (
            self.db.query(UserLearningProfile)
            .filter(UserLearningProfile.user_id == user_id)
            .first()
        )

        if not profile:
            profile = UserLearningProfile(user_id=user_id)
            self.db.add(profile)

        # Update profile with patterns
        profile.formality_level = patterns.get("formality_level", 0.5)
        profile.verbosity = patterns.get("verbosity", 0.5)
        profile.technical_depth = patterns.get("technical_depth", 0.5)
        profile.preferred_response_length = patterns.get(
            "preferred_response_length", 50
        )
        profile.strengths = patterns.get("strengths", [])
        profile.areas_for_improvement = patterns.get("areas_for_improvement", [])
        profile.go_to_phrases = patterns.get("go_to_phrases", [])
        profile.filler_words_used = patterns.get("filler_words", [])
        profile.updated_at = datetime.utcnow()

        # Calculate confidence based on data quantity
        conv_count = (
            self.db.query(func.count(Conversation.id))
            .join(Meeting)
            .filter(Meeting.user_id == user_id)
            .scalar()
        )
        profile.confidence_score = min(conv_count / 100.0, 1.0)

        self.db.commit()
        return profile

    async def get_improvement_suggestions(
        self, user_id: int
    ) -> List[Dict[str, Any]]:
        """Get personalized improvement suggestions for user."""
        profile = (
            self.db.query(UserLearningProfile)
            .filter(UserLearningProfile.user_id == user_id)
            .first()
        )

        if not profile:
            return []

        suggestions = []

        # Analyze areas for improvement
        areas = profile.areas_for_improvement or []
        for area in areas:
            suggestion = await self._generate_suggestion(area, profile)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    async def _generate_suggestion(
        self, area: str, profile: UserLearningProfile
    ) -> Optional[Dict[str, Any]]:
        """Generate a specific improvement suggestion."""
        prompt = f"""The user needs to improve in: {area}

Their current profile:
- Formality level: {profile.formality_level}
- Technical depth: {profile.technical_depth}
- Strengths: {json.dumps(profile.strengths or [])}

Provide ONE specific, actionable suggestion to help them improve in this area.
Format as JSON:
{{
    "area": "{area}",
    "suggestion": "specific actionable advice",
    "example": "an example of good practice",
    "priority": "high/medium/low"
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            return json.loads(content.strip())

        except Exception as e:
            print(f"Suggestion generation error: {e}")
            return None

    async def compare_with_profession(
        self, user_id: int
    ) -> Dict[str, Any]:
        """Compare user's patterns with their profession's best practices."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profession:
            return {"comparison": "No profession set"}

        profile = (
            self.db.query(UserLearningProfile)
            .filter(UserLearningProfile.user_id == user_id)
            .first()
        )

        if not profile:
            return {"comparison": "Not enough data yet"}

        profession = user.profession
        prompt = f"""Compare this user's communication patterns with best practices for a {profession.name}:

User patterns:
- Formality: {profile.formality_level}
- Technical depth: {profile.technical_depth}
- Verbosity: {profile.verbosity}
- Strengths: {json.dumps(profile.strengths or [])}

Profession expectations:
{profession.system_prompt_additions or 'Standard professional communication'}

Provide a comparison in JSON:
{{
    "alignment_score": 0.0-1.0,
    "matches": ["what they do well for their profession"],
    "gaps": ["where they could better align with profession standards"],
    "recommendations": ["specific tips"]
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

            return json.loads(content.strip())

        except Exception as e:
            print(f"Profession comparison error: {e}")
            return {"comparison": f"Error: {str(e)}"}
