"""Context Provider for AI personalization based on profession and ML learning."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import threading
import json


class ContextProvider:
    """Provides personalized context for AI responses based on user profile."""

    # Cache duration in seconds
    CACHE_DURATION = 300  # 5 minutes

    def __init__(self, api_client):
        self.api = api_client
        self._profession_context: Optional[Dict] = None
        self._learning_profile: Optional[Dict] = None
        self._topic_analytics: Optional[Dict] = None
        self._last_fetch: Optional[datetime] = None
        self._lock = threading.Lock()

    def refresh_context(self, force: bool = False) -> bool:
        """Refresh context from backend."""
        if not self.api.is_logged_in():
            return False

        # Check cache
        if not force and self._last_fetch:
            age = (datetime.now() - self._last_fetch).total_seconds()
            if age < self.CACHE_DURATION:
                return True

        with self._lock:
            try:
                # Fetch full AI context
                context = self.api.get_ai_context()
                if "error" not in context:
                    self._profession_context = context.get("profession")
                    self._learning_profile = context.get("learning_profile")
                    self._topic_analytics = context.get("topics")
                    self._last_fetch = datetime.now()
                    return True

                # Fallback: fetch individually
                prof = self.api.get_user_profession_context()
                if "error" not in prof:
                    self._profession_context = prof

                learning = self.api.get_learning_profile()
                if "error" not in learning:
                    self._learning_profile = learning

                topics = self.api.get_topic_analytics()
                if "error" not in topics:
                    self._topic_analytics = topics

                self._last_fetch = datetime.now()
                return True

            except Exception as e:
                print(f"Failed to refresh context: {e}")
                return False

    def get_system_prompt_additions(self, meeting_type: str = "general") -> str:
        """Get personalized system prompt additions based on context."""
        parts = []

        # Add profession context
        if self._profession_context:
            prof = self._profession_context
            if prof.get("name"):
                parts.append(f"The user is a {prof['name']}.")

            if prof.get("system_prompt_additions"):
                parts.append(prof["system_prompt_additions"])

            if prof.get("terminology"):
                terms = prof["terminology"]
                if isinstance(terms, list) and terms:
                    parts.append(f"Use industry terminology when appropriate: {', '.join(terms[:10])}.")

            if prof.get("communication_style"):
                style = prof["communication_style"]
                if style == "formal":
                    parts.append("Maintain a formal, professional tone.")
                elif style == "technical":
                    parts.append("Use technical language appropriate for their field.")
                elif style == "creative":
                    parts.append("Be creative and engaging in communication style.")
                elif style == "empathetic":
                    parts.append("Use an empathetic and supportive tone.")

        # Add ML learning profile personalization
        if self._learning_profile:
            profile = self._learning_profile

            # Formality
            formality = profile.get("formality_level", 0.5)
            if formality > 0.7:
                parts.append("The user prefers formal, professional responses.")
            elif formality < 0.3:
                parts.append("The user prefers casual, conversational responses.")

            # Verbosity
            verbosity = profile.get("verbosity", 0.5)
            if verbosity > 0.7:
                parts.append("The user appreciates detailed, comprehensive answers.")
            elif verbosity < 0.3:
                parts.append("Keep responses concise and to the point.")

            # Response length
            pref_length = profile.get("preferred_response_length")
            if pref_length:
                if pref_length < 30:
                    parts.append("Aim for very brief responses (under 30 words).")
                elif pref_length > 100:
                    parts.append("The user prefers more detailed responses.")

            # Strengths
            strengths = profile.get("strengths")
            if strengths and isinstance(strengths, list) and strengths:
                parts.append(f"Build on user's strengths: {', '.join(strengths[:3])}.")

            # Go-to phrases
            phrases = profile.get("go_to_phrases")
            if phrases and isinstance(phrases, list) and phrases:
                parts.append(f"The user often uses phrases like: {', '.join(phrases[:3])}.")

        # Add meeting-type specific guidance
        meeting_guidance = self._get_meeting_type_guidance(meeting_type)
        if meeting_guidance:
            parts.append(meeting_guidance)

        return " ".join(parts)

    def _get_meeting_type_guidance(self, meeting_type: str) -> str:
        """Get guidance specific to meeting type."""
        guidance = {
            "interview": "This is a job interview. Help with clear, confident responses using the STAR method when appropriate. Highlight achievements and skills.",
            "manager": "This is a 1:1 with a manager. Focus on updates, blockers, and professional growth. Be structured but conversational.",
            "client": "This is a client meeting. Be professional, solution-focused, and attentive to client needs.",
            "sales": "This is a sales call. Focus on value proposition, handling objections, and building rapport.",
            "tv": "This is a TV/media appearance. Keep responses quotable, concise, and memorable. Avoid jargon.",
            "presentation": "This is a presentation. Focus on clarity, key messages, and audience engagement.",
            "training": "This is a training session. Be educational, patient, and use examples.",
        }
        return guidance.get(meeting_type, "")

    def get_relevant_topics(self, limit: int = 5) -> List[str]:
        """Get user's most discussed topics for context."""
        if not self._topic_analytics:
            return []

        topics = self._topic_analytics.get("topics", [])
        if isinstance(topics, list):
            return [t.get("name", t) if isinstance(t, dict) else str(t) for t in topics[:limit]]
        return []

    def get_briefing_context(self, participant_names: List[str] = None,
                             meeting_context: str = None) -> Optional[Dict]:
        """Get pre-meeting briefing from backend."""
        if not self.api.is_logged_in():
            return None

        return self.api.generate_briefing(
            participant_names=participant_names,
            meeting_context=meeting_context,
            meeting_type="general"
        )

    def get_participant_memory(self, name: str) -> Optional[Dict]:
        """Get remembered information about a participant."""
        if not self.api.is_logged_in():
            return None
        return self.api.get_participant(name)

    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current context state."""
        return {
            "has_profession": self._profession_context is not None,
            "profession_name": self._profession_context.get("name") if self._profession_context else None,
            "has_learning_profile": self._learning_profile is not None,
            "learning_confidence": self._learning_profile.get("confidence_score") if self._learning_profile else None,
            "topic_count": len(self._topic_analytics.get("topics", [])) if self._topic_analytics else 0,
            "last_refresh": self._last_fetch.isoformat() if self._last_fetch else None,
            "cache_age_seconds": (datetime.now() - self._last_fetch).total_seconds() if self._last_fetch else None
        }

    def build_enhanced_system_prompt(self, base_prompt: str, meeting_type: str = "general") -> str:
        """Build an enhanced system prompt with all context."""
        additions = self.get_system_prompt_additions(meeting_type)

        if additions:
            return f"{base_prompt}\n\n{additions}"
        return base_prompt

    def clear_cache(self) -> None:
        """Clear cached context."""
        with self._lock:
            self._profession_context = None
            self._learning_profile = None
            self._topic_analytics = None
            self._last_fetch = None
