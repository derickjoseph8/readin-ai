"""
Admin routes for Chat QA and review management.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel

from database import get_db
from auth import get_current_user
from models import (
    User, ChatSession, ChatMessage, ChatQARecord,
    TeamMember, SupportTeam, StaffRole
)

router = APIRouter(prefix="/admin/qa", tags=["Admin - QA"])


def require_staff(user: User):
    """Verify user is a staff member."""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")


def require_admin(user: User):
    """Verify user is admin or super_admin."""
    if not user.is_staff or user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")


# =============================================================================
# SCHEMAS
# =============================================================================

class ChatSessionSummary(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str]
    user_email: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str]
    team_name: Optional[str]
    status: str
    is_ai_handled: bool
    ai_resolution_status: Optional[str]
    message_count: int
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]
    has_qa_review: bool


class ChatTranscript(BaseModel):
    session: ChatSessionSummary
    messages: List[dict]


class QAReviewCreate(BaseModel):
    overall_score: int  # 1-5
    response_time_score: Optional[int] = None  # 1-5
    resolution_score: Optional[int] = None  # 1-5
    professionalism_score: Optional[int] = None  # 1-5
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class QAReviewResponse(BaseModel):
    id: int
    session_id: int
    reviewer_id: int
    reviewer_name: Optional[str]
    overall_score: int
    response_time_score: Optional[int]
    resolution_score: Optional[int]
    professionalism_score: Optional[int]
    notes: Optional[str]
    tags: List[str]
    reviewed_at: datetime


class QAMetrics(BaseModel):
    total_sessions: int
    reviewed_sessions: int
    review_rate: float
    avg_overall_score: float
    avg_response_time_score: float
    avg_resolution_score: float
    avg_professionalism_score: float
    ai_handled_count: int
    ai_resolved_count: int
    ai_transferred_count: int
    agent_handled_count: int


# =============================================================================
# CHAT SESSIONS FOR QA
# =============================================================================

@router.get("/sessions")
async def get_qa_sessions(
    status: str = Query("ended", pattern="^(ended|all)$"),
    agent_id: Optional[int] = None,
    team_id: Optional[int] = None,
    is_ai_handled: Optional[bool] = None,
    has_review: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List chat sessions for QA review."""
    require_admin(current_user)

    query = db.query(ChatSession)

    if status == "ended":
        query = query.filter(ChatSession.status == "ended")

    if agent_id:
        query = query.filter(ChatSession.agent_id == agent_id)

    if team_id:
        query = query.filter(ChatSession.team_id == team_id)

    if is_ai_handled is not None:
        query = query.filter(ChatSession.is_ai_handled == is_ai_handled)

    if start_date:
        query = query.filter(ChatSession.started_at >= start_date)

    if end_date:
        query = query.filter(ChatSession.started_at <= end_date)

    total = query.count()
    sessions = query.order_by(ChatSession.started_at.desc()).offset(offset).limit(limit).all()

    result = []
    for session in sessions:
        # Get user info
        user = db.query(User).filter(User.id == session.user_id).first()

        # Get agent info
        agent_name = None
        if session.agent_id:
            member = db.query(TeamMember).filter(TeamMember.id == session.agent_id).first()
            if member:
                agent_user = db.query(User).filter(User.id == member.user_id).first()
                agent_name = agent_user.full_name if agent_user else None

        # Get team info
        team = db.query(SupportTeam).filter(SupportTeam.id == session.team_id).first() if session.team_id else None

        # Count messages
        message_count = db.query(func.count(ChatMessage.id)).filter(
            ChatMessage.session_id == session.id
        ).scalar()

        # Check for QA review
        has_qa = db.query(ChatQARecord).filter(ChatQARecord.session_id == session.id).first() is not None

        # Filter by has_review if specified
        if has_review is not None and has_qa != has_review:
            continue

        # Calculate duration
        duration = None
        if session.ended_at and session.started_at:
            duration = int((session.ended_at - session.started_at).total_seconds() / 60)

        result.append(ChatSessionSummary(
            id=session.id,
            user_id=session.user_id,
            user_name=user.full_name if user else None,
            user_email=user.email if user else None,
            agent_id=session.agent_id,
            agent_name=agent_name,
            team_name=team.name if team else None,
            status=session.status,
            is_ai_handled=session.is_ai_handled or False,
            ai_resolution_status=session.ai_resolution_status,
            message_count=message_count,
            started_at=session.started_at,
            ended_at=session.ended_at,
            duration_minutes=duration,
            has_qa_review=has_qa
        ))

    return {
        "sessions": result,
        "total": total
    }


@router.get("/sessions/{session_id}/transcript", response_model=ChatTranscript)
async def get_session_transcript(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full transcript for a chat session."""
    require_admin(current_user)

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get user info
    user = db.query(User).filter(User.id == session.user_id).first()

    # Get agent info
    agent_name = None
    if session.agent_id:
        member = db.query(TeamMember).filter(TeamMember.id == session.agent_id).first()
        if member:
            agent_user = db.query(User).filter(User.id == member.user_id).first()
            agent_name = agent_user.full_name if agent_user else None

    # Get team info
    team = db.query(SupportTeam).filter(SupportTeam.id == session.team_id).first() if session.team_id else None

    # Get messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at).all()

    # Count messages
    message_count = len(messages)

    # Check for QA review
    has_qa = db.query(ChatQARecord).filter(ChatQARecord.session_id == session.id).first() is not None

    # Calculate duration
    duration = None
    if session.ended_at and session.started_at:
        duration = int((session.ended_at - session.started_at).total_seconds() / 60)

    summary = ChatSessionSummary(
        id=session.id,
        user_id=session.user_id,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
        agent_id=session.agent_id,
        agent_name=agent_name,
        team_name=team.name if team else None,
        status=session.status,
        is_ai_handled=session.is_ai_handled or False,
        ai_resolution_status=session.ai_resolution_status,
        message_count=message_count,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=duration,
        has_qa_review=has_qa
    )

    message_list = []
    for msg in messages:
        sender_name = None
        if msg.sender_type == "customer":
            sender_name = user.full_name if user else "Customer"
        elif msg.sender_type == "agent":
            sender_name = agent_name or "Agent"
        elif msg.sender_type == "bot":
            sender_name = "Novah (AI)"
        else:
            sender_name = "System"

        message_list.append({
            "id": msg.id,
            "sender_type": msg.sender_type,
            "sender_name": sender_name,
            "message": msg.message,
            "message_type": msg.message_type,
            "created_at": msg.created_at.isoformat()
        })

    return ChatTranscript(
        session=summary,
        messages=message_list
    )


# =============================================================================
# QA REVIEWS
# =============================================================================

@router.post("/sessions/{session_id}/review", response_model=QAReviewResponse)
async def submit_qa_review(
    session_id: int,
    review_data: QAReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a QA review for a chat session."""
    require_admin(current_user)

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if already reviewed
    existing = db.query(ChatQARecord).filter(ChatQARecord.session_id == session_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Session already reviewed")

    # Validate scores
    for score in [review_data.overall_score, review_data.response_time_score,
                  review_data.resolution_score, review_data.professionalism_score]:
        if score is not None and (score < 1 or score > 5):
            raise HTTPException(status_code=400, detail="Scores must be between 1 and 5")

    review = ChatQARecord(
        session_id=session_id,
        reviewer_id=current_user.id,
        overall_score=review_data.overall_score,
        response_time_score=review_data.response_time_score,
        resolution_score=review_data.resolution_score,
        professionalism_score=review_data.professionalism_score,
        notes=review_data.notes,
        tags=review_data.tags or []
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return QAReviewResponse(
        id=review.id,
        session_id=review.session_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=current_user.full_name,
        overall_score=review.overall_score,
        response_time_score=review.response_time_score,
        resolution_score=review.resolution_score,
        professionalism_score=review.professionalism_score,
        notes=review.notes,
        tags=review.tags or [],
        reviewed_at=review.reviewed_at
    )


@router.get("/sessions/{session_id}/review", response_model=Optional[QAReviewResponse])
async def get_qa_review(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get QA review for a session."""
    require_admin(current_user)

    review = db.query(ChatQARecord).filter(ChatQARecord.session_id == session_id).first()
    if not review:
        return None

    reviewer = db.query(User).filter(User.id == review.reviewer_id).first()

    return QAReviewResponse(
        id=review.id,
        session_id=review.session_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=reviewer.full_name if reviewer else None,
        overall_score=review.overall_score,
        response_time_score=review.response_time_score,
        resolution_score=review.resolution_score,
        professionalism_score=review.professionalism_score,
        notes=review.notes,
        tags=review.tags or [],
        reviewed_at=review.reviewed_at
    )


# =============================================================================
# QA METRICS
# =============================================================================

@router.get("/metrics", response_model=QAMetrics)
async def get_qa_metrics(
    days: int = Query(30, ge=1, le=365),
    agent_id: Optional[int] = None,
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get QA metrics and statistics."""
    require_admin(current_user)

    start_date = datetime.utcnow() - timedelta(days=days)

    # Base query for sessions
    session_query = db.query(ChatSession).filter(
        and_(
            ChatSession.status == "ended",
            ChatSession.started_at >= start_date
        )
    )

    if agent_id:
        session_query = session_query.filter(ChatSession.agent_id == agent_id)
    if team_id:
        session_query = session_query.filter(ChatSession.team_id == team_id)

    sessions = session_query.all()
    total_sessions = len(sessions)

    # Count reviewed sessions
    reviewed_sessions = db.query(func.count(ChatQARecord.id)).filter(
        ChatQARecord.session_id.in_([s.id for s in sessions])
    ).scalar() or 0

    # Calculate average scores
    review_query = db.query(ChatQARecord).filter(
        ChatQARecord.session_id.in_([s.id for s in sessions])
    )
    reviews = review_query.all()

    avg_overall = sum(r.overall_score for r in reviews) / len(reviews) if reviews else 0
    avg_response = sum(r.response_time_score for r in reviews if r.response_time_score) / len([r for r in reviews if r.response_time_score]) if any(r.response_time_score for r in reviews) else 0
    avg_resolution = sum(r.resolution_score for r in reviews if r.resolution_score) / len([r for r in reviews if r.resolution_score]) if any(r.resolution_score for r in reviews) else 0
    avg_professional = sum(r.professionalism_score for r in reviews if r.professionalism_score) / len([r for r in reviews if r.professionalism_score]) if any(r.professionalism_score for r in reviews) else 0

    # AI handling stats
    ai_handled = sum(1 for s in sessions if s.is_ai_handled)
    ai_resolved = sum(1 for s in sessions if s.ai_resolution_status == "resolved_by_ai")
    ai_transferred = sum(1 for s in sessions if s.ai_resolution_status == "transferred")
    agent_handled = total_sessions - ai_handled

    return QAMetrics(
        total_sessions=total_sessions,
        reviewed_sessions=reviewed_sessions,
        review_rate=reviewed_sessions / total_sessions * 100 if total_sessions > 0 else 0,
        avg_overall_score=round(avg_overall, 2),
        avg_response_time_score=round(avg_response, 2),
        avg_resolution_score=round(avg_resolution, 2),
        avg_professionalism_score=round(avg_professional, 2),
        ai_handled_count=ai_handled,
        ai_resolved_count=ai_resolved,
        ai_transferred_count=ai_transferred,
        agent_handled_count=agent_handled
    )
