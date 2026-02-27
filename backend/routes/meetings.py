"""Meeting API routes - Meeting lifecycle and summary management."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db

logger = logging.getLogger(__name__)
from models import Meeting, Conversation, MeetingSummary, ActionItem, Commitment, User
from schemas import (
    MeetingCreate, MeetingEnd, MeetingResponse, MeetingDetail, MeetingList,
    MeetingSummaryResponse, MeetingSummaryRequest,
    ConversationResponse, ActionItemResponse, CommitmentResponse
)
from auth import get_current_user

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post("", response_model=MeetingResponse)
def start_meeting(
    data: MeetingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new meeting session.
    Called by desktop app when user begins a meeting.
    """
    meeting = Meeting(
        user_id=user.id,
        meeting_type=data.meeting_type,
        title=data.title,
        meeting_app=data.meeting_app,
        participant_count=data.participant_count,
        status="active"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    return MeetingResponse(
        id=meeting.id,
        meeting_type=meeting.meeting_type,
        title=meeting.title,
        meeting_app=meeting.meeting_app,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration_seconds=meeting.duration_seconds,
        status=meeting.status,
        participant_count=meeting.participant_count,
        conversation_count=0
    )


@router.post("/{meeting_id}/end", response_model=MeetingResponse)
def end_meeting(
    meeting_id: int,
    data: MeetingEnd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End a meeting session.
    Optionally triggers summary generation and email.
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

    if meeting.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meeting is not active"
        )

    # End meeting
    meeting.ended_at = datetime.utcnow()
    meeting.duration_seconds = int((meeting.ended_at - meeting.started_at).total_seconds())
    meeting.status = "ended"
    meeting.notes = data.notes

    # Count conversations
    conv_count = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id
    ).count()

    db.commit()
    db.refresh(meeting)

    # Trigger async summary generation if requested and there are conversations
    if data.generate_summary and conv_count > 0:
        try:
            from workers.tasks.summary_generation import generate_meeting_summary
            # Check user's email preference
            send_email = data.send_email and getattr(user, 'email_summary_enabled', True)
            generate_meeting_summary.delay(meeting_id, user.id, send_email)
            logger.info(f"Triggered summary generation for meeting {meeting_id}")
        except Exception as e:
            # Don't fail the request if async task fails to queue
            logger.error(f"Failed to queue summary generation: {e}")

    return MeetingResponse(
        id=meeting.id,
        meeting_type=meeting.meeting_type,
        title=meeting.title,
        meeting_app=meeting.meeting_app,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration_seconds=meeting.duration_seconds,
        status=meeting.status,
        participant_count=meeting.participant_count,
        conversation_count=conv_count
    )


@router.get("", response_model=MeetingList)
def list_meetings(
    meeting_type: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's meetings with filters."""
    query = db.query(Meeting).filter(Meeting.user_id == user.id)

    if meeting_type:
        query = query.filter(Meeting.meeting_type == meeting_type)
    if status:
        query = query.filter(Meeting.status == status)
    if from_date:
        query = query.filter(Meeting.started_at >= from_date)
    if to_date:
        query = query.filter(Meeting.started_at <= to_date)

    total = query.count()
    meetings = query.order_by(desc(Meeting.started_at)).offset(skip).limit(limit).all()

    # Get conversation counts
    meeting_ids = [m.id for m in meetings]
    conv_counts = {}
    if meeting_ids:
        counts = db.query(
            Conversation.meeting_id,
            func.count(Conversation.id)
        ).filter(
            Conversation.meeting_id.in_(meeting_ids)
        ).group_by(Conversation.meeting_id).all()
        conv_counts = dict(counts)

    return MeetingList(
        meetings=[
            MeetingResponse(
                id=m.id,
                meeting_type=m.meeting_type,
                title=m.title,
                meeting_app=m.meeting_app,
                started_at=m.started_at,
                ended_at=m.ended_at,
                duration_seconds=m.duration_seconds,
                status=m.status,
                participant_count=m.participant_count,
                conversation_count=conv_counts.get(m.id, 0)
            )
            for m in meetings
        ],
        total=total
    )


@router.get("/active", response_model=Optional[MeetingResponse])
def get_active_meeting(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's current active meeting, if any."""
    meeting = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.status == "active"
    ).order_by(desc(Meeting.started_at)).first()

    if not meeting:
        return None

    conv_count = db.query(Conversation).filter(
        Conversation.meeting_id == meeting.id
    ).count()

    return MeetingResponse(
        id=meeting.id,
        meeting_type=meeting.meeting_type,
        title=meeting.title,
        meeting_app=meeting.meeting_app,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration_seconds=meeting.duration_seconds,
        status=meeting.status,
        participant_count=meeting.participant_count,
        conversation_count=conv_count
    )


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get meeting details with conversations, action items, and summary."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Get conversations
    conversations = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id
    ).order_by(Conversation.timestamp).all()

    # Get action items
    action_items = db.query(ActionItem).filter(
        ActionItem.meeting_id == meeting_id
    ).order_by(ActionItem.created_at).all()

    # Get commitments
    commitments = db.query(Commitment).filter(
        Commitment.meeting_id == meeting_id
    ).order_by(Commitment.created_at).all()

    # Get summary
    summary = db.query(MeetingSummary).filter(
        MeetingSummary.meeting_id == meeting_id
    ).first()

    return MeetingDetail(
        id=meeting.id,
        meeting_type=meeting.meeting_type,
        title=meeting.title,
        meeting_app=meeting.meeting_app,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration_seconds=meeting.duration_seconds,
        status=meeting.status,
        participant_count=meeting.participant_count,
        conversation_count=len(conversations),
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        action_items=[ActionItemResponse.model_validate(a) for a in action_items],
        commitments=[CommitmentResponse.model_validate(c) for c in commitments],
        summary=MeetingSummaryResponse.model_validate(summary) if summary else None
    )


@router.patch("/{meeting_id}")
def update_meeting(
    meeting_id: int,
    title: Optional[str] = None,
    meeting_type: Optional[str] = None,
    notes: Optional[str] = None,
    participant_count: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update meeting details."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    if title is not None:
        meeting.title = title
    if meeting_type is not None:
        meeting.meeting_type = meeting_type
    if notes is not None:
        meeting.notes = notes
    if participant_count is not None:
        meeting.participant_count = participant_count

    db.commit()

    return {"message": "Meeting updated"}


@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a meeting and all associated data."""
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Delete cascades to conversations, action items, commitments, summary
    db.delete(meeting)
    db.commit()

    return {"message": "Meeting deleted"}


@router.get("/{meeting_id}/summary", response_model=MeetingSummaryResponse)
def get_meeting_summary(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the summary for a meeting."""
    # Verify meeting belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    summary = db.query(MeetingSummary).filter(
        MeetingSummary.meeting_id == meeting_id
    ).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not generated yet"
        )

    return MeetingSummaryResponse.model_validate(summary)


@router.post("/{meeting_id}/summary", response_model=MeetingSummaryResponse)
async def generate_summary(
    meeting_id: int,
    data: MeetingSummaryRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate or regenerate meeting summary.
    Extracts key points, action items, and commitments.
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

    # Get existing summary
    summary = db.query(MeetingSummary).filter(
        MeetingSummary.meeting_id == meeting_id
    ).first()

    if summary and not data.regenerate:
        return MeetingSummaryResponse.model_validate(summary)

    # Get conversations for summarization
    conversations = db.query(Conversation).filter(
        Conversation.meeting_id == meeting_id
    ).order_by(Conversation.timestamp).all()

    if not conversations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversations to summarize"
        )

    # TODO: Use AI to generate summary
    # For now, create placeholder summary
    if summary:
        summary.summary_text = f"Meeting summary for {meeting.title or 'Untitled Meeting'}"
        summary.key_points = ["Key point 1", "Key point 2"]
        summary.decisions_made = []
        summary.topics_discussed = []
    else:
        summary = MeetingSummary(
            meeting_id=meeting_id,
            user_id=user.id,
            summary_text=f"Meeting summary for {meeting.title or 'Untitled Meeting'}",
            key_points=["Key point 1", "Key point 2"],
            decisions_made=[],
            topics_discussed=[],
            sentiment="neutral"
        )
        db.add(summary)

    db.commit()
    db.refresh(summary)

    # Send email if requested and user has email summaries enabled
    if data.send_email and getattr(user, 'email_summary_enabled', True):
        async def send_summary_email():
            try:
                from services.email_service import EmailService
                email_service = EmailService(db)
                await email_service.send_meeting_summary_email(
                    user_id=user.id,
                    summary_id=summary.id,
                )
                logger.info(f"Meeting summary email sent to user {user.id} for meeting {meeting_id}")
            except Exception as e:
                logger.error(f"Failed to send meeting summary email: {e}")

        background_tasks.add_task(asyncio.create_task, send_summary_email())

    return MeetingSummaryResponse.model_validate(summary)


@router.get("/{meeting_id}/smart-prep")
def get_smart_prep(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered smart preparation for a meeting.
    Returns participant insights, suggested talking points, relevant past discussions,
    and recommended questions to help users prepare effectively.
    """
    from models import ParticipantMemory, Topic, Commitment

    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Agenda items (from meeting title and notes)
    agenda_items = []
    if meeting.title:
        agenda_items.append({"item": meeting.title, "priority": "high"})
    if meeting.notes:
        # Parse notes for bullet points or numbered items
        lines = meeting.notes.split('\n')
        for line in lines[:5]:  # First 5 lines
            if line.strip():
                agenda_items.append({"item": line.strip(), "priority": "normal"})

    # Get participant insights from memory
    participant_insights = []
    # Get participants from recent similar meetings
    recent_meetings = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.meeting_type == meeting.meeting_type,
        Meeting.id != meeting_id
    ).order_by(desc(Meeting.started_at)).limit(5).all()

    # Get all participant memories
    participant_memories = db.query(ParticipantMemory).filter(
        ParticipantMemory.user_id == user.id
    ).order_by(desc(ParticipantMemory.last_interaction)).limit(10).all()

    for pm in participant_memories:
        participant_insights.append({
            "name": pm.participant_name,
            "role": pm.participant_role,
            "company": pm.company,
            "communication_style": pm.communication_style,
            "key_interests": pm.topics_discussed[:3] if pm.topics_discussed else [],
            "last_interaction": pm.last_interaction.isoformat() if pm.last_interaction else None,
            "relationship_notes": pm.relationship_notes
        })

    # Suggested talking points based on user's expertise and meeting type
    user_topics = db.query(Topic).filter(
        Topic.user_id == user.id
    ).order_by(desc(Topic.frequency)).limit(10).all()

    suggested_talking_points = []
    meeting_type_prompts = {
        "interview": [
            "Share your key accomplishments and their impact",
            "Explain your problem-solving approach with examples",
            "Discuss your experience with relevant technologies"
        ],
        "sales": [
            "Lead with the value proposition",
            "Address common objections proactively",
            "Share relevant case studies or success stories"
        ],
        "tv_appearance": [
            "Open with a compelling sound bite",
            "Bridge to your key message within first 30 seconds",
            "Use concrete examples and data points"
        ],
        "team_meeting": [
            "Start with quick wins and progress updates",
            "Address blockers and request specific help needed",
            "Align on next steps with clear owners"
        ],
        "one_on_one": [
            "Ask about their priorities and challenges",
            "Share updates on mutual commitments",
            "Discuss growth opportunities and feedback"
        ]
    }

    # Add meeting type specific points
    if meeting.meeting_type in meeting_type_prompts:
        for point in meeting_type_prompts[meeting.meeting_type]:
            suggested_talking_points.append({
                "point": point,
                "source": "best_practice"
            })

    # Add user's top topics as talking points
    for topic in user_topics[:5]:
        suggested_talking_points.append({
            "point": f"Discuss your expertise in {topic.name}",
            "source": "your_expertise"
        })

    # Get relevant past discussions from similar meetings
    relevant_past_discussions = []
    for past_meeting in recent_meetings:
        conversations = db.query(Conversation).filter(
            Conversation.meeting_id == past_meeting.id
        ).order_by(desc(Conversation.timestamp)).limit(3).all()

        if conversations:
            relevant_past_discussions.append({
                "meeting_title": past_meeting.title or f"{past_meeting.meeting_type} meeting",
                "date": past_meeting.started_at.isoformat(),
                "key_points": [c.ai_response[:150] + "..." if len(c.ai_response) > 150 else c.ai_response for c in conversations]
            })

    # Get pending commitments and action items
    pending_commitments = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending"
    ).order_by(Commitment.due_date.asc().nullslast()).limit(5).all()

    pending_action_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status.in_(["pending", "in_progress"])
    ).order_by(ActionItem.due_date.asc().nullslast()).limit(5).all()

    follow_up_items = []
    for c in pending_commitments:
        follow_up_items.append({
            "type": "commitment",
            "description": c.commitment_text,
            "due_date": c.due_date.isoformat() if c.due_date else None,
            "context": c.context
        })
    for ai in pending_action_items:
        follow_up_items.append({
            "type": "action_item",
            "description": ai.description,
            "due_date": ai.due_date.isoformat() if ai.due_date else None,
            "assignee": ai.assignee
        })

    # Generate recommended questions based on meeting type
    recommended_questions = {
        "interview": [
            "What does success look like in this role in the first 90 days?",
            "What are the biggest challenges the team is currently facing?",
            "How would you describe the company culture?"
        ],
        "sales": [
            "What's driving your evaluation of solutions right now?",
            "Who else is involved in this decision?",
            "What would need to be true for this to move forward?"
        ],
        "team_meeting": [
            "What blockers can I help remove for the team?",
            "Are there any risks or concerns we should discuss?",
            "What's our top priority for this sprint?"
        ],
        "one_on_one": [
            "What's been on your mind lately?",
            "How can I better support you?",
            "What feedback do you have for me?"
        ],
        "tv_appearance": [
            "What angle is the show taking on this topic?",
            "Who else is being interviewed?",
            "What questions should I expect?"
        ]
    }

    return {
        "meeting_id": meeting.id,
        "meeting_type": meeting.meeting_type,
        "meeting_title": meeting.title,
        "agenda_items": agenda_items,
        "participant_insights": participant_insights[:5],  # Top 5
        "suggested_talking_points": suggested_talking_points[:10],  # Top 10
        "relevant_past_discussions": relevant_past_discussions[:3],  # Last 3 similar meetings
        "follow_up_items": follow_up_items[:5],  # Top 5 pending items
        "recommended_questions": recommended_questions.get(meeting.meeting_type, [
            "What are your main objectives for this meeting?",
            "What challenges are you currently facing?",
            "How can we best move forward together?"
        ]),
        "prep_generated_at": datetime.utcnow().isoformat()
    }


@router.get("/analytics/overview")
def meeting_analytics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get meeting analytics for the user."""
    # Total meetings
    total = db.query(Meeting).filter(Meeting.user_id == user.id).count()

    # By type
    type_counts = db.query(
        Meeting.meeting_type,
        func.count(Meeting.id)
    ).filter(Meeting.user_id == user.id).group_by(Meeting.meeting_type).all()

    # Total conversations
    conv_total = db.query(Conversation).join(Meeting).filter(
        Meeting.user_id == user.id
    ).count()

    # Average duration
    avg_duration = db.query(func.avg(Meeting.duration_seconds)).filter(
        Meeting.user_id == user.id,
        Meeting.duration_seconds.isnot(None)
    ).scalar()

    # This week
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= week_ago
    ).count()

    # This month
    month_ago = datetime.utcnow() - timedelta(days=30)
    this_month = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= month_ago
    ).count()

    return {
        "total_meetings": total,
        "meetings_by_type": dict(type_counts),
        "total_conversations": conv_total,
        "average_meeting_duration": float(avg_duration) if avg_duration else None,
        "meetings_this_week": this_week,
        "meetings_this_month": this_month
    }
