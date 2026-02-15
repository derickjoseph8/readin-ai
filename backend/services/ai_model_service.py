"""
AI Model selection and management service.

Provides:
- Model selection (Sonnet, Opus, Haiku)
- Cost estimation and tracking
- Model performance comparison
- User preference management
"""

from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import User, UserAIPreferences
from config import IS_PRODUCTION


class AIModel(str, Enum):
    """Available Claude AI models."""
    SONNET = "sonnet"
    OPUS = "opus"
    HAIKU = "haiku"


@dataclass
class ModelInfo:
    """Information about an AI model."""
    id: str
    name: str
    description: str
    speed: str  # fast, medium, slow
    quality: str  # good, better, best
    cost_per_1k_input: float  # USD
    cost_per_1k_output: float  # USD
    max_tokens: int
    best_for: list


# Model configurations
MODELS = {
    AIModel.HAIKU: ModelInfo(
        id="claude-3-haiku-20240307",
        name="Claude Haiku",
        description="Fastest model for simple tasks",
        speed="fast",
        quality="good",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        max_tokens=4096,
        best_for=["Quick responses", "Simple questions", "High volume", "Cost-sensitive"],
    ),
    AIModel.SONNET: ModelInfo(
        id="claude-sonnet-4-20250514",
        name="Claude Sonnet",
        description="Balanced model for most tasks",
        speed="medium",
        quality="better",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=8192,
        best_for=["General meetings", "Technical discussions", "Summaries", "Balanced cost/quality"],
    ),
    AIModel.OPUS: ModelInfo(
        id="claude-opus-4-20250514",
        name="Claude Opus",
        description="Most capable model for complex tasks",
        speed="slow",
        quality="best",
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        max_tokens=8192,
        best_for=["Complex analysis", "Important meetings", "Detailed briefings", "High-stakes interviews"],
    ),
}


class AIModelService:
    """
    Service for managing AI model selection and preferences.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_available_models(self) -> list:
        """Get list of available models with their info."""
        return [
            {
                "id": model.value,
                "api_id": info.id,
                "name": info.name,
                "description": info.description,
                "speed": info.speed,
                "quality": info.quality,
                "cost_per_1k_input": info.cost_per_1k_input,
                "cost_per_1k_output": info.cost_per_1k_output,
                "max_tokens": info.max_tokens,
                "best_for": info.best_for,
            }
            for model, info in MODELS.items()
        ]

    def get_user_preferences(self, user_id: int) -> Optional[UserAIPreferences]:
        """Get user's AI preferences."""
        return self.db.query(UserAIPreferences).filter(
            UserAIPreferences.user_id == user_id
        ).first()

    def get_or_create_preferences(self, user_id: int) -> UserAIPreferences:
        """Get or create user's AI preferences."""
        prefs = self.get_user_preferences(user_id)
        if not prefs:
            prefs = UserAIPreferences(user_id=user_id)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
        return prefs

    def update_preferences(
        self,
        user_id: int,
        **updates,
    ) -> UserAIPreferences:
        """Update user's AI preferences."""
        prefs = self.get_or_create_preferences(user_id)

        for key, value in updates.items():
            if hasattr(prefs, key) and value is not None:
                setattr(prefs, key, value)

        self.db.commit()
        self.db.refresh(prefs)
        return prefs

    def get_model_for_user(
        self,
        user_id: int,
        meeting_type: Optional[str] = None,
    ) -> str:
        """
        Get the appropriate model API ID for a user.

        Considers:
        - User preferences
        - Meeting type
        - Budget constraints
        - Subscription status
        """
        prefs = self.get_user_preferences(user_id)
        user = self.db.query(User).filter(User.id == user_id).first()

        # Default to Sonnet
        model = AIModel.SONNET

        if prefs:
            model = AIModel(prefs.preferred_model)

            # Check budget
            if prefs.monthly_budget_cents:
                if prefs.current_month_usage_cents >= prefs.monthly_budget_cents:
                    # Over budget, use cheapest model
                    model = AIModel.HAIKU

        # Trial users get Haiku to manage costs
        if user and user.subscription_status == "trial":
            # Allow Sonnet for interviews, Haiku for general
            if meeting_type in ["interview", "tv_appearance"]:
                model = AIModel.SONNET
            else:
                model = AIModel.HAIKU

        return MODELS[model].id

    def estimate_cost(
        self,
        model: AIModel,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost in USD for a request."""
        info = MODELS[model]
        input_cost = (input_tokens / 1000) * info.cost_per_1k_input
        output_cost = (output_tokens / 1000) * info.cost_per_1k_output
        return input_cost + output_cost

    def record_usage(
        self,
        user_id: int,
        model: AIModel,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record AI usage for cost tracking."""
        prefs = self.get_or_create_preferences(user_id)

        cost_cents = int(self.estimate_cost(model, input_tokens, output_tokens) * 100)
        prefs.current_month_usage_cents += cost_cents

        # Check if we need to reset (new month)
        if prefs.updated_at and prefs.updated_at.month != datetime.utcnow().month:
            prefs.current_month_usage_cents = cost_cents

        self.db.commit()

        # Check budget alert
        if prefs.monthly_budget_cents:
            usage_ratio = prefs.current_month_usage_cents / prefs.monthly_budget_cents
            if usage_ratio >= prefs.budget_alert_threshold:
                self._send_budget_alert(user_id, usage_ratio)

    def _send_budget_alert(self, user_id: int, usage_ratio: float):
        """Send budget alert notification."""
        # TODO: Integrate with notification service
        pass

    def get_model_recommendation(
        self,
        meeting_type: str,
        expected_duration_minutes: int,
        importance: str = "normal",
    ) -> Dict[str, Any]:
        """
        Get model recommendation based on meeting context.

        Args:
            meeting_type: Type of meeting
            expected_duration_minutes: Expected duration
            importance: low, normal, high

        Returns:
            Recommendation with model and reasoning
        """
        # High importance or interviews -> Opus
        if importance == "high" or meeting_type in ["interview", "tv_appearance"]:
            return {
                "recommended": AIModel.OPUS.value,
                "reason": "High-stakes meeting benefits from best quality responses",
                "alternatives": [AIModel.SONNET.value],
            }

        # Long meetings -> Sonnet (balanced)
        if expected_duration_minutes > 60:
            return {
                "recommended": AIModel.SONNET.value,
                "reason": "Extended meetings benefit from balanced quality and cost",
                "alternatives": [AIModel.OPUS.value, AIModel.HAIKU.value],
            }

        # Short/simple meetings -> Haiku
        if expected_duration_minutes < 15 or meeting_type == "general":
            return {
                "recommended": AIModel.HAIKU.value,
                "reason": "Quick meetings work well with fast responses",
                "alternatives": [AIModel.SONNET.value],
            }

        # Default to Sonnet
        return {
            "recommended": AIModel.SONNET.value,
            "reason": "Best balance of quality, speed, and cost for most meetings",
            "alternatives": [AIModel.OPUS.value, AIModel.HAIKU.value],
        }

    def get_usage_summary(self, user_id: int) -> Dict[str, Any]:
        """Get user's AI usage summary for the current month."""
        prefs = self.get_user_preferences(user_id)

        if not prefs:
            return {
                "current_month_cents": 0,
                "budget_cents": None,
                "usage_ratio": 0,
                "estimated_monthly": 0,
            }

        # Estimate monthly usage based on current pace
        now = datetime.utcnow()
        days_in_month = 30
        days_elapsed = now.day
        daily_rate = prefs.current_month_usage_cents / max(days_elapsed, 1)
        estimated_monthly = daily_rate * days_in_month

        return {
            "current_month_cents": prefs.current_month_usage_cents,
            "budget_cents": prefs.monthly_budget_cents,
            "usage_ratio": (
                prefs.current_month_usage_cents / prefs.monthly_budget_cents
                if prefs.monthly_budget_cents else 0
            ),
            "estimated_monthly_cents": int(estimated_monthly),
            "preferred_model": prefs.preferred_model,
        }
