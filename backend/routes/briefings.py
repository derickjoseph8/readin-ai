"""Briefings API routes - Pre-meeting preparation and participant memory."""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
from models import (
    Meeting, Conversation, ParticipantMemory, Commitment, ActionItem,
    Topic, MediaAppearance, User
)
from schemas import (
    BriefingRequest, BriefingResponse, ParticipantBriefing,
    ParticipantMemoryCreate, ParticipantMemoryUpdate, ParticipantMemoryResponse,
    ParticipantMemoryList, CommitmentResponse
)
from auth import get_current_user

router = APIRouter(prefix="/briefings", tags=["Briefings"])


@router.post("/generate", response_model=BriefingResponse)
def generate_briefing(
    data: BriefingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a pre-meeting briefing.
    Provides context, participant history, and suggested talking points.
    """
    participant_context = []

    # Get participant memories if provided
    if data.participant_names:
        for name in data.participant_names:
            memory = db.query(ParticipantMemory).filter(
                ParticipantMemory.user_id == user.id,
                ParticipantMemory.participant_name.ilike(f"%{name}%")
            ).first()

            if memory:
                participant_context.append({
                    "name": memory.participant_name,
                    "role": memory.participant_role,
                    "company": memory.company,
                    "key_points": memory.key_points or [],
                    "communication_style": memory.communication_style,
                    "last_interaction": memory.last_interaction.isoformat() if memory.last_interaction else None,
                    "topics_they_care_about": memory.topics_discussed or []
                })
            else:
                participant_context.append({
                    "name": name,
                    "note": "No previous interaction history"
                })

    # Get suggested topics based on user's expertise
    user_topics = db.query(Topic).filter(
        Topic.user_id == user.id
    ).order_by(desc(Topic.frequency)).limit(10).all()
    suggested_topics = [t.name for t in user_topics]

    # Topics to avoid (for media appearances)
    topics_to_avoid = []
    if data.meeting_type == "tv_appearance":
        # Get recently discussed points to suggest variety
        recent_appearances = db.query(MediaAppearance).filter(
            MediaAppearance.user_id == user.id
        ).order_by(desc(MediaAppearance.created_at)).limit(5).all()

        recent_points = set()
        for app in recent_appearances:
            if app.points_made:
                recent_points.update(app.points_made[:3])  # First 3 points from each
        topics_to_avoid = list(recent_points)[:5]

    # Get unfulfilled commitments related to participants
    past_commitments = []
    if data.participant_names:
        for name in data.participant_names:
            # Search commitments mentioning participant
            commitments = db.query(Commitment).filter(
                Commitment.user_id == user.id,
                Commitment.status == "pending",
                Commitment.context.ilike(f"%{name}%")
            ).all()
            past_commitments.extend(commitments)

    # Get action items to follow up on
    key_points_to_follow_up = []
    pending_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status.in_(["pending", "in_progress"]),
        ActionItem.assignee_role == "other"
    ).order_by(ActionItem.due_date.asc().nullslast()).limit(5).all()

    for item in pending_items:
        key_points_to_follow_up.append(
            f"Follow up with {item.assignee} on: {item.description[:100]}"
        )

    return BriefingResponse(
        meeting_type=data.meeting_type,
        participant_context=participant_context,
        suggested_topics=suggested_topics,
        topics_to_avoid=topics_to_avoid,
        past_commitments=[CommitmentResponse.model_validate(c) for c in past_commitments],
        key_points_to_follow_up=key_points_to_follow_up,
        generated_at=datetime.utcnow()
    )


# ============== Participant Memory ==============

@router.post("/participants", response_model=ParticipantMemoryResponse)
def create_participant_memory(
    data: ParticipantMemoryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new participant memory entry."""
    # Check if already exists
    existing = db.query(ParticipantMemory).filter(
        ParticipantMemory.user_id == user.id,
        ParticipantMemory.participant_name.ilike(data.participant_name)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Participant already exists. Use update endpoint."
        )

    memory = ParticipantMemory(
        user_id=user.id,
        participant_name=data.participant_name,
        participant_email=data.participant_email,
        participant_role=data.participant_role,
        company=data.company,
        relationship_notes=data.relationship_notes
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    return ParticipantMemoryResponse.model_validate(memory)


@router.get("/participants", response_model=ParticipantMemoryList)
def list_participants(
    search: Optional[str] = None,
    company: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all participant memories."""
    query = db.query(ParticipantMemory).filter(
        ParticipantMemory.user_id == user.id
    )

    if search:
        query = query.filter(
            ParticipantMemory.participant_name.ilike(f"%{search}%")
        )
    if company:
        query = query.filter(
            ParticipantMemory.company.ilike(f"%{company}%")
        )

    total = query.count()
    participants = query.order_by(
        desc(ParticipantMemory.last_interaction)
    ).offset(skip).limit(limit).all()

    return ParticipantMemoryList(
        participants=[ParticipantMemoryResponse.model_validate(p) for p in participants],
        total=total
    )


@router.get("/participants/{participant_id}", response_model=ParticipantMemoryResponse)
def get_participant(
    participant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific participant's memory."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    return ParticipantMemoryResponse.model_validate(memory)


@router.get("/participants/by-name/{name}", response_model=ParticipantMemoryResponse)
def get_participant_by_name(
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get participant memory by name (case-insensitive search)."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.user_id == user.id,
        ParticipantMemory.participant_name.ilike(f"%{name}%")
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    return ParticipantMemoryResponse.model_validate(memory)


@router.patch("/participants/{participant_id}", response_model=ParticipantMemoryResponse)
def update_participant(
    participant_id: int,
    data: ParticipantMemoryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update participant memory."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    if data.participant_role is not None:
        memory.participant_role = data.participant_role
    if data.company is not None:
        memory.company = data.company
    if data.relationship_notes is not None:
        memory.relationship_notes = data.relationship_notes
    if data.key_points is not None:
        memory.key_points = data.key_points
    if data.preferences is not None:
        memory.preferences = data.preferences

    db.commit()
    db.refresh(memory)

    return ParticipantMemoryResponse.model_validate(memory)


@router.post("/participants/{participant_id}/add-point")
def add_key_point(
    participant_id: int,
    point: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a key point to participant's memory."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    if memory.key_points is None:
        memory.key_points = []

    memory.key_points = memory.key_points + [point]
    memory.last_interaction = datetime.utcnow()
    db.commit()

    return {"message": "Key point added"}


@router.post("/participants/{participant_id}/add-topic")
def add_topic(
    participant_id: int,
    topic: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a discussion topic to participant's memory."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    if memory.topics_discussed is None:
        memory.topics_discussed = []

    if topic not in memory.topics_discussed:
        memory.topics_discussed = memory.topics_discussed + [topic]

    memory.last_interaction = datetime.utcnow()
    db.commit()

    return {"message": "Topic added"}


@router.delete("/participants/{participant_id}")
def delete_participant(
    participant_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a participant memory."""
    memory = db.query(ParticipantMemory).filter(
        ParticipantMemory.id == participant_id,
        ParticipantMemory.user_id == user.id
    ).first()

    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found"
        )

    db.delete(memory)
    db.commit()

    return {"message": "Participant deleted"}


@router.post("/participants/auto-extract")
def auto_extract_participants(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Auto-extract participants from meeting conversations.
    Uses AI to identify speakers and what they said.
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    conversations = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id,
        Conversation.speaker != "user"
    ).all()

    # TODO: Use AI to extract speaker names and key points
    # For now, return placeholder
    return {
        "message": "Participant extraction queued",
        "conversation_count": len(conversations),
        "note": "AI will analyze conversations and create participant memories"
    }
