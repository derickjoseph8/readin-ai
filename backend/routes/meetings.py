"""Meeting API routes - Meeting lifecycle and summary management."""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db
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

    # TODO: Trigger async summary generation if requested
    # if data.generate_summary:
    #     generate_meeting_summary.delay(meeting_id, data.send_email)

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
def generate_summary(
    meeting_id: int,
    data: MeetingSummaryRequest,
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

    # TODO: Send email if requested
    # if data.send_email and user.email_summary_enabled:
    #     send_summary_email.delay(user.id, summary.id)

    return MeetingSummaryResponse.model_validate(summary)


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
