"""
Metrics and monitoring API routes.

Provides:
- Application metrics endpoint (JSON)
- Prometheus metrics endpoint (text/plain)
- System health details
- Performance statistics
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Meeting, Conversation
from auth import get_current_user
from middleware.logging_middleware import (
    metrics,
    get_prometheus_metrics,
    get_prometheus_content_type,
    set_active_users,
)
from config import IS_PRODUCTION

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
def get_metrics(db: Session = Depends(get_db)):
    """
    Get application metrics in JSON format.

    In production, this should be protected or disabled.
    """
    if IS_PRODUCTION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Metrics endpoint disabled in production"
        )

    return metrics.get_metrics()


@router.get("/prometheus")
def prometheus_metrics(request: Request, db: Session = Depends(get_db)):
    """
    Get application metrics in Prometheus format.

    This endpoint is designed to be scraped by Prometheus.
    In production, protect this endpoint via network policies or auth.
    """
    # Update active users gauge before generating metrics
    try:
        active_user_count = db.query(func.count(User.id)).filter(
            User.subscription_status.in_(["trial", "active"])
        ).scalar() or 0
        set_active_users(active_user_count)
    except Exception:
        pass  # Don't fail if we can't get user count

    return Response(
        content=get_prometheus_metrics(),
        media_type=get_prometheus_content_type()
    )


@router.get("/health/detailed")
def detailed_health(db: Session = Depends(get_db)):
    """
    Detailed health check with database statistics.
    """
    try:
        # Database stats
        user_count = db.query(func.count(User.id)).scalar()
        meeting_count = db.query(func.count(Meeting.id)).scalar()
        active_meetings = db.query(func.count(Meeting.id)).filter(
            Meeting.status == "active"
        ).scalar()

        # Recent activity
        from datetime import timedelta
        day_ago = datetime.utcnow() - timedelta(days=1)
        meetings_24h = db.query(func.count(Meeting.id)).filter(
            Meeting.started_at >= day_ago
        ).scalar()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "total_users": user_count,
                "total_meetings": meeting_count,
                "active_meetings": active_meetings,
                "meetings_last_24h": meetings_24h,
            },
            "application": metrics.get_metrics(),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)[:100],
        }


@router.get("/user/stats")
def user_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for the current user.
    """
    from datetime import timedelta

    # Total meetings
    total_meetings = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id
    ).scalar()

    # Total conversations
    total_conversations = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id
    ).scalar()

    # Total meeting time
    total_duration = db.query(func.sum(Meeting.duration_seconds)).filter(
        Meeting.user_id == user.id,
        Meeting.duration_seconds.isnot(None)
    ).scalar() or 0

    # This week
    week_ago = datetime.utcnow() - timedelta(days=7)
    meetings_this_week = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= week_ago
    ).scalar()

    # This month
    month_ago = datetime.utcnow() - timedelta(days=30)
    meetings_this_month = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= month_ago
    ).scalar()

    # Average meeting duration
    avg_duration = db.query(func.avg(Meeting.duration_seconds)).filter(
        Meeting.user_id == user.id,
        Meeting.duration_seconds.isnot(None)
    ).scalar()

    # Meetings by type
    meetings_by_type = db.query(
        Meeting.meeting_type,
        func.count(Meeting.id)
    ).filter(
        Meeting.user_id == user.id
    ).group_by(Meeting.meeting_type).all()

    return {
        "user_id": user.id,
        "total_meetings": total_meetings,
        "total_conversations": total_conversations,
        "total_meeting_hours": round(total_duration / 3600, 1),
        "meetings_this_week": meetings_this_week,
        "meetings_this_month": meetings_this_month,
        "avg_meeting_minutes": round((avg_duration or 0) / 60, 1),
        "meetings_by_type": dict(meetings_by_type),
        "member_since": user.created_at.isoformat() if user.created_at else None,
    }
