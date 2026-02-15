"""AI model preferences and settings endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserAIPreferences
from auth import get_current_user
from services.ai_model_service import AIModelService, AIModel

router = APIRouter(prefix="/ai", tags=["AI Preferences"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AIPreferencesUpdate(BaseModel):
    """Request to update AI preferences."""
    preferred_model: Optional[str] = Field(None, description="sonnet, opus, or haiku")
    fallback_model: Optional[str] = None
    response_length: Optional[str] = Field(None, description="short, medium, or long")
    response_style: Optional[str] = Field(None, description="professional, casual, technical")
    bullet_points: Optional[bool] = None
    include_sources: Optional[bool] = None
    monthly_budget_cents: Optional[int] = Field(None, ge=0)
    budget_alert_threshold: Optional[float] = Field(None, ge=0, le=1)
    temperature: Optional[float] = Field(None, ge=0, le=1)
    max_tokens: Optional[int] = Field(None, ge=100, le=8192)
    custom_instructions: Optional[str] = None


class AIPreferencesResponse(BaseModel):
    """AI preferences response."""
    preferred_model: str
    fallback_model: str
    response_length: str
    response_style: str
    bullet_points: bool
    include_sources: bool
    monthly_budget_cents: Optional[int]
    current_month_usage_cents: int
    budget_alert_threshold: float
    temperature: float
    max_tokens: int
    custom_instructions: Optional[str]

    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    """AI model information."""
    id: str
    api_id: str
    name: str
    description: str
    speed: str
    quality: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    best_for: list


class ModelRecommendation(BaseModel):
    """Model recommendation response."""
    recommended: str
    reason: str
    alternatives: list


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/models")
def list_models(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List available AI models with their capabilities and pricing.
    """
    service = AIModelService(db)
    models = service.get_available_models()

    # Get user's current preference
    prefs = service.get_user_preferences(user.id)
    current_model = prefs.preferred_model if prefs else "sonnet"

    return {
        "models": models,
        "current_selection": current_model,
    }


@router.get("/preferences", response_model=AIPreferencesResponse)
def get_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current AI preferences."""
    service = AIModelService(db)
    prefs = service.get_or_create_preferences(user.id)
    return AIPreferencesResponse.model_validate(prefs)


@router.put("/preferences", response_model=AIPreferencesResponse)
def update_preferences(
    request: AIPreferencesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update AI preferences."""
    # Validate model names
    if request.preferred_model:
        try:
            AIModel(request.preferred_model)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model: {request.preferred_model}. Must be sonnet, opus, or haiku.",
            )

    service = AIModelService(db)
    prefs = service.update_preferences(
        user.id,
        **request.model_dump(exclude_unset=True),
    )
    return AIPreferencesResponse.model_validate(prefs)


@router.get("/recommend", response_model=ModelRecommendation)
def get_recommendation(
    meeting_type: str = "general",
    duration_minutes: int = 30,
    importance: str = "normal",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI model recommendation based on meeting context.

    Args:
        meeting_type: Type of meeting (general, interview, tv_appearance, etc.)
        duration_minutes: Expected meeting duration
        importance: low, normal, or high
    """
    service = AIModelService(db)
    recommendation = service.get_model_recommendation(
        meeting_type=meeting_type,
        expected_duration_minutes=duration_minutes,
        importance=importance,
    )
    return ModelRecommendation(**recommendation)


@router.get("/usage")
def get_usage_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI usage summary for the current month."""
    service = AIModelService(db)
    return service.get_usage_summary(user.id)


@router.post("/estimate-cost")
def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Estimate cost for a specific AI request.

    Returns cost in USD.
    """
    try:
        model_enum = AIModel(model)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model: {model}",
        )

    service = AIModelService(db)
    cost = service.estimate_cost(model_enum, input_tokens, output_tokens)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": round(cost, 6),
        "estimated_cost_cents": int(cost * 100),
    }


@router.post("/set-budget")
def set_budget(
    monthly_budget_cents: int = 1000,  # $10 default
    alert_threshold: float = 0.8,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set monthly AI usage budget.

    Args:
        monthly_budget_cents: Budget in cents (e.g., 1000 = $10)
        alert_threshold: Alert when usage reaches this ratio (0-1)
    """
    service = AIModelService(db)
    prefs = service.update_preferences(
        user.id,
        monthly_budget_cents=monthly_budget_cents,
        budget_alert_threshold=alert_threshold,
    )

    return {
        "monthly_budget_cents": prefs.monthly_budget_cents,
        "current_usage_cents": prefs.current_month_usage_cents,
        "alert_threshold": prefs.budget_alert_threshold,
        "message": f"Budget set to ${monthly_budget_cents / 100:.2f}/month",
    }
