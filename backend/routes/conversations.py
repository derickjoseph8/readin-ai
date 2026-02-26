"""Conversation API routes - Store and analyze meeting conversations."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
from models import Conversation, Meeting, Topic, ConversationTopic, User, UserLearningProfile
from schemas import ConversationCreate, ConversationResponse, TopicResponse, TopicAnalytics
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    background_tasks: BackgroundTasks,
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

    # Trigger async topic extraction in background
    async def extract_topics_async(conv_id: int, uid: int):
        try:
            from database import SessionLocal
            from services.topic_extractor import TopicExtractor
            db_session = SessionLocal()
            try:
                extractor = TopicExtractor(db_session)
                conv = db_session.query(Conversation).filter(Conversation.id == conv_id).first()
                if conv:
                    await extractor.process_conversation(conv, uid)
                    logger.info(f"Topic extraction completed for conversation {conv_id}")
            finally:
                db_session.close()
        except Exception as e:
            logger.error(f"Topic extraction failed for conversation {conv_id}: {e}")

    background_tasks.add_task(asyncio.create_task, extract_topics_async(conversation.id, user.id))

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
async def trigger_topic_extraction(
    meeting_id: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
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

    # Trigger async topic extraction for all conversations
    async def process_conversations(convs, uid):
        try:
            from services.topic_extractor import TopicExtractor
            extractor = TopicExtractor(db)
            for conv in convs:
                try:
                    await extractor.process_conversation(conv, uid)
                except Exception as e:
                    logger.error(f"Topic extraction failed for conv {conv.id}: {e}")
            await extractor.update_learning_profile_topics(uid)
            logger.info(f"Topic extraction completed for {len(convs)} conversations")
        except Exception as e:
            logger.error(f"Batch topic extraction failed: {e}")

    if background_tasks:
        background_tasks.add_task(asyncio.create_task, process_conversations(conversations, user.id))
    else:
        await process_conversations(conversations, user.id)

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
async def update_learning_profile(
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

    # Run ML analysis with Claude to analyze communication patterns
    try:
        from services.topic_extractor import TopicExtractor
        extractor = TopicExtractor(db)
        await extractor.update_learning_profile_topics(user.id)

        # Analyze recent conversations for communication style
        recent_convs = db.query(Conversation).join(Meeting).filter(
            Meeting.user_id == user.id
        ).order_by(desc(Conversation.timestamp)).limit(50).all()

        if recent_convs:
            # Calculate average response length
            response_lengths = [
                len(c.response_text) for c in recent_convs
                if c.response_text
            ]
            if response_lengths:
                avg_length = sum(response_lengths) / len(response_lengths)
                if avg_length > 500:
                    profile.verbosity = 0.8
                    profile.preferred_response_length = "detailed"
                elif avg_length > 200:
                    profile.verbosity = 0.5
                    profile.preferred_response_length = "moderate"
                else:
                    profile.verbosity = 0.3
                    profile.preferred_response_length = "concise"

        profile.confidence_score = min(0.9, total_convs / 100.0)
        logger.info(f"Updated learning profile for user {user.id}")
    except Exception as e:
        logger.error(f"Learning profile ML analysis failed: {e}")

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
