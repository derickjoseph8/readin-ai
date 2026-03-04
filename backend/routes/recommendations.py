"""
AI-Powered Meeting Recommendations API Routes.

Provides endpoints for:
- GET /meetings/{id}/recommendations - Full meeting recommendations
- GET /meetings/{id}/next-steps - Next steps suggestions
- GET /meetings/{id}/risks - Risk detection
- GET /meetings/{id}/prep - Meeting preparation hints
- GET /participants/{id}/insights - Participant insights
- GET /recommendations/topics - Topic suggestions
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from models import Meeting, User, ParticipantMemory
from auth import get_current_user
from services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class NextStepsResponse(BaseModel):
    """Response schema for next steps endpoint."""
    meeting_id: int
    next_steps: List[str]
    count: int


class RiskItem(BaseModel):
    """Schema for a single risk item."""
    category: str
    title: str
    description: str
    severity: str
    evidence: Optional[str] = None
    mitigation: Optional[str] = None
    meeting_id: int
    detected_at: str


class RisksResponse(BaseModel):
    """Response schema for risks endpoint."""
    meeting_id: int
    risks: List[RiskItem]
    count: int
    has_critical: bool
    has_high: bool


class MeetingPrepResponse(BaseModel):
    """Response schema for meeting prep endpoint."""
    meeting_id: int
    key_topics: List[str] = []
    suggested_agenda: List[str] = []
    participant_notes: List[str] = []
    questions_to_consider: List[str] = []
    documents_to_review: List[str] = []
    talking_points: List[str] = []
    follow_up_items: List[str] = []
    preparation_tips: List[str] = []
    generated_at: Optional[str] = None


class ParticipantInsightsResponse(BaseModel):
    """Response schema for participant insights."""
    participant_id: int
    participant_name: str
    relationship_summary: Optional[str] = None
    communication_recommendations: List[str] = []
    topics_of_interest: List[str] = []
    conversation_starters: List[str] = []
    things_to_remember: List[str] = []
    collaboration_tips: List[str] = []
    potential_opportunities: List[str] = []
    relationship_health: Optional[str] = None
    next_interaction_suggestions: List[str] = []
    generated_at: Optional[str] = None


class TopicSuggestionsResponse(BaseModel):
    """Response schema for topic suggestions."""
    topics: List[str]
    meeting_type: Optional[str] = None
    count: int


class FullRecommendationsResponse(BaseModel):
    """Response schema for full meeting recommendations."""
    meeting_id: int
    meeting_title: Optional[str] = None
    meeting_type: Optional[str] = None
    next_steps: List[str] = []
    risks: List[dict] = []
    action_items: List[dict] = []
    commitments: List[dict] = []
    summary: dict = {}
    generated_at: str
    has_urgent_items: bool = False
    has_high_risks: bool = False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def verify_meeting_access(db: Session, meeting_id: int, user: User) -> Meeting:
    """Verify user has access to the meeting."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    return meeting


# =============================================================================
# MEETING RECOMMENDATION ENDPOINTS
# =============================================================================

@router.get("/meetings/{meeting_id}", response_model=FullRecommendationsResponse)
async def get_meeting_recommendations(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive AI-powered recommendations for a meeting.

    Returns next steps, risk analysis, action items, commitments,
    and summary all in one response.
    """
    verify_meeting_access(db, meeting_id, user)

    service = RecommendationService(db)
    recommendations = await service.get_meeting_recommendations(
        meeting_id=meeting_id,
        language=user.preferred_language,
    )

    if recommendations.get("error"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=recommendations["error"]
        )

    return FullRecommendationsResponse(**recommendations)


@router.get("/meetings/{meeting_id}/next-steps", response_model=NextStepsResponse)
async def get_next_steps(
    meeting_id: int,
    max_steps: int = Query(5, ge=1, le=10, description="Maximum number of steps"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI-suggested next steps based on meeting content.

    Analyzes the meeting transcript, summary, and action items
    to generate prioritized next steps.
    """
    verify_meeting_access(db, meeting_id, user)

    service = RecommendationService(db)
    next_steps = await service.get_next_steps(
        meeting_id=meeting_id,
        max_steps=max_steps,
        language=user.preferred_language,
    )

    return NextStepsResponse(
        meeting_id=meeting_id,
        next_steps=next_steps,
        count=len(next_steps),
    )


@router.get("/meetings/{meeting_id}/risks", response_model=RisksResponse)
async def get_meeting_risks(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Identify potential risks from meeting content.

    Analyzes meeting for:
    - Missed or unrealistic deadlines
    - Unclear commitments
    - Potential conflicts
    - Resource concerns
    - Communication issues
    """
    verify_meeting_access(db, meeting_id, user)

    service = RecommendationService(db)
    risks = await service.detect_risks(
        meeting_id=meeting_id,
        language=user.preferred_language,
    )

    return RisksResponse(
        meeting_id=meeting_id,
        risks=risks,
        count=len(risks),
        has_critical=any(r.get("severity") == "critical" for r in risks),
        has_high=any(r.get("severity") == "high" for r in risks),
    )


@router.get("/meetings/{meeting_id}/prep", response_model=MeetingPrepResponse)
async def get_meeting_prep(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI-powered preparation hints for a meeting.

    Analyzes past meetings with similar participants, topics,
    and meeting type to provide preparation guidance.
    """
    verify_meeting_access(db, meeting_id, user)

    service = RecommendationService(db)
    prep = await service.get_meeting_prep(
        meeting_id=meeting_id,
        language=user.preferred_language,
    )

    if prep.get("error") and not prep.get("key_topics"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=prep.get("error", "Failed to generate preparation hints")
        )

    return MeetingPrepResponse(**prep)


# =============================================================================
# PARTICIPANT INSIGHTS ENDPOINT
# =============================================================================

@router.get("/participants/{participant_id}/insights", response_model=ParticipantInsightsResponse)
async def get_participant_insights(
    participant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI-powered insights about a participant across meetings.

    Analyzes all interactions with a participant to provide
    communication insights and relationship guidance.
    """
    # Verify participant belongs to user
    participant = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    service = RecommendationService(db)
    insights = await service.get_participant_insights(
        participant_id=participant_id,
        user_id=user.id,
        language=user.preferred_language,
    )

    if insights.get("error") and not insights.get("relationship_summary"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=insights.get("error", "Failed to generate insights")
        )

    return ParticipantInsightsResponse(**insights)


# =============================================================================
# TOPIC SUGGESTIONS ENDPOINT
# =============================================================================

@router.get("/topics", response_model=TopicSuggestionsResponse)
async def get_topic_suggestions(
    meeting_type: Optional[str] = Query(
        None,
        description="Filter by meeting type (interview, tv_appearance, general, etc.)"
    ),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get AI-suggested topics based on meeting history.

    Analyzes past meetings, topics discussed, and user's expertise
    areas to suggest relevant topics for future meetings.
    """
    service = RecommendationService(db)
    topics = await service.get_topic_suggestions(
        user_id=user.id,
        meeting_type=meeting_type,
        limit=limit,
        language=user.preferred_language,
    )

    return TopicSuggestionsResponse(
        topics=topics,
        meeting_type=meeting_type,
        count=len(topics),
    )


# =============================================================================
# ADDITIONAL CONVENIENCE ENDPOINTS ON MEETINGS ROUTER
# =============================================================================

# Create a separate router for meeting-specific endpoints
# that can be added to the meetings router
meetings_recommendations_router = APIRouter(tags=["Meetings"])


@meetings_recommendations_router.get("/meetings/{meeting_id}/recommendations")
async def get_meeting_recommendations_alt(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Alias for /recommendations/meetings/{id}

    Get comprehensive AI-powered recommendations for a meeting.
    """
    return await get_meeting_recommendations(meeting_id, user, db)


@meetings_recommendations_router.get("/meetings/{meeting_id}/next-steps")
async def get_next_steps_alt(
    meeting_id: int,
    max_steps: int = Query(5, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Alias for /recommendations/meetings/{id}/next-steps

    Get AI-suggested next steps based on meeting content.
    """
    return await get_next_steps(meeting_id, max_steps, user, db)


@meetings_recommendations_router.get("/meetings/{meeting_id}/risks")
async def get_risks_alt(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Alias for /recommendations/meetings/{id}/risks

    Identify potential risks from meeting content.
    """
    return await get_meeting_risks(meeting_id, user, db)


@meetings_recommendations_router.get("/participants/{participant_id}/insights")
async def get_participant_insights_alt(
    participant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Alias for /recommendations/participants/{id}/insights

    Get AI-powered insights about a participant.
    """
    return await get_participant_insights(participant_id, user, db)
