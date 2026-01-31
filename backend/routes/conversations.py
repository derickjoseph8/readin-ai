"""Conversation API routes - Store and analyze meeting conversations."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
from models import Conversation, Meeting, Topic, ConversationTopic, User, UserLearningProfile
from schemas import ConversationCreate, ConversationResponse, TopicResponse, TopicAnalytics
from auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Store a conversation exchange from a meeting.
    Called by desktop app for each Q&A pair.
    """
    # Verify meeting belongs to user and is active
    meeting = db.query(Meeting).filter(
        Meeting.id == data.meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    if meeting.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting is not active"
        )

    conversation = Conversation(
        meeting_id=data.meeting_id,
        speaker=data.speaker,
        heard_text=data.heard_text,
        response_text=data.response_text
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    # TODO: Trigger async topic extraction
    # extract_topics.delay(conversation.id, user.id)

    return ConversationResponse.model_validate(conversation)


@router.get("/meeting/{meeting_id}", response_model=List[ConversationResponse])
def list_meeting_conversations(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations from a specific meeting."""
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
        Conversation.meeting_id == meeting_id
    ).order_by(Conversation.timestamp).all()

    return [ConversationResponse.model_validate(c) for c in conversations]


@router.get("/topics", response_model=TopicAnalytics)
def get_user_topics(
    category: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's discussion topics with frequency analytics.
    Used for ML learning and pattern recognition.
    """
    query = db.query(Topic).filter(Topic.user_id == user.id)

    if category:
        query = query.filter(Topic.category == category)

    topics = query.order_by(desc(Topic.frequency)).limit(limit).all()

    # Get category counts
    category_counts = db.query(
        Topic.category,
        func.count(Topic.id)
    ).filter(
        Topic.user_id == user.id
    ).group_by(Topic.category).all()

    total = db.query(Topic).filter(Topic.user_id == user.id).count()

    return TopicAnalytics(
        topics=[TopicResponse.model_validate(t) for t in topics],
        total_topics=total,
        top_categories=dict(category_counts)
    )


@router.post("/topics/extract")
def trigger_topic_extraction(
    meeting_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger topic extraction for conversations.
    If meeting_id is provided, extract from that meeting only.
    Otherwise, extract from all unprocessed conversations.
    """
    if meeting_id:
        # Verify meeting
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
            Conversation.meeting_id == meeting_id
        ).all()
    else:
        # Get conversations without topics
        processed_conv_ids = db.query(ConversationTopic.conversation_id).distinct()
        conversations = db.query(Conversation).join(Meeting).filter(
            Meeting.user_id == user.id,
            ~Conversation.id.in_(processed_conv_ids)
        ).limit(100).all()

    # TODO: Async topic extraction with Claude
    # for conv in conversations:
    #     extract_topics.delay(conv.id, user.id)

    return {
        "message": f"Topic extraction queued for {len(conversations)} conversations",
        "conversation_count": len(conversations)
    }


@router.get("/search")
def search_conversations(
    query: str,
    meeting_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search user's conversation history.
    Useful for pre-meeting briefings and context retrieval.
    """
    conv_query = db.query(Conversation).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.heard_text.ilike(f"%{query}%")
    )

    if meeting_type:
        conv_query = conv_query.filter(Meeting.meeting_type == meeting_type)
    if from_date:
        conv_query = conv_query.filter(Meeting.started_at >= from_date)
    if to_date:
        conv_query = conv_query.filter(Meeting.started_at <= to_date)

    conversations = conv_query.order_by(desc(Conversation.timestamp)).limit(limit).all()

    return {
        "query": query,
        "count": len(conversations),
        "results": [
            {
                "id": c.id,
                "meeting_id": c.meeting_id,
                "heard_text": c.heard_text,
                "response_text": c.response_text,
                "timestamp": c.timestamp.isoformat(),
                "meeting_type": c.meeting.meeting_type
            }
            for c in conversations
        ]
    }


@router.get("/learning-profile")
def get_learning_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the ML-learned profile of user's communication patterns.
    Used to personalize AI responses based on user's style.
    """
    profile = db.query(UserLearningProfile).filter(
        UserLearningProfile.user_id == user.id
    ).first()

    if not profile:
        return {
            "has_profile": False,
            "message": "Not enough data yet. Keep using ReadIn AI to build your profile.",
            "conversations_needed": 10
        }

    # Get topic expertise
    topics = db.query(Topic).filter(
        Topic.user_id == user.id
    ).order_by(desc(Topic.frequency)).limit(10).all()

    return {
        "has_profile": True,
        "profile": {
            "formality_level": profile.formality_level,
            "verbosity": profile.verbosity,
            "technical_depth": profile.technical_depth,
            "preferred_response_length": profile.preferred_response_length,
            "strengths": profile.strengths or [],
            "areas_for_improvement": profile.areas_for_improvement or [],
            "go_to_phrases": profile.go_to_phrases or [],
            "confidence_score": profile.confidence_score,
            "total_conversations_analyzed": profile.total_conversations_analyzed
        },
        "top_topics": [
            {
                "name": t.name,
                "category": t.category,
                "frequency": t.frequency
            }
            for t in topics
        ],
        "last_updated": profile.updated_at.isoformat() if profile.updated_at else None
    }


@router.post("/learning-profile/update")
def update_learning_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger ML profile update based on recent conversations.
    Analyzes patterns and updates user's communication style profile.
    """
    # Get profile or create
    profile = db.query(UserLearningProfile).filter(
        UserLearningProfile.user_id == user.id
    ).first()

    if not profile:
        profile = UserLearningProfile(user_id=user.id)
        db.add(profile)

    # Count conversations
    total_convs = db.query(Conversation).join(Meeting).filter(
        Meeting.user_id == user.id
    ).count()

    profile.total_conversations_analyzed = total_convs

    # TODO: Run ML analysis with Claude
    # Analyze formality, verbosity, technical depth, patterns, etc.

    db.commit()

    return {
        "message": "Learning profile update triggered",
        "conversations_analyzed": total_convs
    }


@router.get("/context")
def get_conversation_context(
    topics: Optional[str] = None,
    participant_name: Optional[str] = None,
    limit: int = 5,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get relevant past conversation context.
    Used by AI to provide context-aware responses.

    This is the key endpoint for ML-based personalization:
    1. Before registration: Use profession's stored knowledge
    2. After learning user: Use user's personal patterns and history
    """
    context_data = {
        "profession_context": None,
        "personal_context": None,
        "relevant_conversations": [],
        "topic_history": []
    }

    # 1. Get profession context (stored knowledge for their career)
    if user.profession:
        context_data["profession_context"] = {
            "name": user.profession.name,
            "terminology": user.profession.terminology or {},
            "communication_style": user.profession.communication_style,
            "common_topics": user.profession.common_topics or [],
            "system_prompt": user.profession.system_prompt_additions
        }

    # 2. Get personal learning profile (after ML has learned the user)
    profile = db.query(UserLearningProfile).filter(
        UserLearningProfile.user_id == user.id
    ).first()

    if profile and profile.confidence_score > 0.3:  # Only use if confident enough
        context_data["personal_context"] = {
            "formality_level": profile.formality_level,
            "verbosity": profile.verbosity,
            "technical_depth": profile.technical_depth,
            "preferred_response_length": profile.preferred_response_length,
            "strengths": profile.strengths or [],
            "go_to_phrases": profile.go_to_phrases or [],
            "confidence": profile.confidence_score
        }

    # 3. Get relevant past conversations
    if topics:
        topic_list = [t.strip() for t in topics.split(",")]
        # Search for conversations mentioning these topics
        for topic in topic_list[:3]:
            convs = db.query(Conversation).join(Meeting).filter(
                Meeting.user_id == user.id,
                Conversation.heard_text.ilike(f"%{topic}%")
            ).order_by(desc(Conversation.timestamp)).limit(2).all()

            for c in convs:
                context_data["relevant_conversations"].append({
                    "topic": topic,
                    "heard": c.heard_text[:200],
                    "response": c.response_text[:200] if c.response_text else None,
                    "when": c.timestamp.isoformat()
                })

    # 4. Get user's frequent topics
    frequent_topics = db.query(Topic).filter(
        Topic.user_id == user.id
    ).order_by(desc(Topic.frequency)).limit(10).all()

    context_data["topic_history"] = [
        {
            "name": t.name,
            "category": t.category,
            "frequency": t.frequency,
            "last_discussed": t.last_discussed.isoformat()
        }
        for t in frequent_topics
    ]

    return context_data
