"""
Comprehensive analytics dashboard API endpoints.

Provides:
- Meeting statistics and trends
- Topic analysis
- Action item metrics
- AI usage and cost tracking
- User engagement metrics
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, and_, or_, case, extract
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, Meeting, Conversation, ActionItem, Topic, DailyUsage,
    MeetingSummary, Commitment, AnalyticsEvent
)
from auth import get_current_user

router = APIRouter(prefix="/analytics/dashboard", tags=["Analytics Dashboard"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TimeRange(str, Enum):
    """Time range options for analytics."""
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


class MeetingStats(BaseModel):
    """Meeting statistics."""
    total_meetings: int
    total_duration_minutes: int
    avg_duration_minutes: float
    meetings_by_type: dict
    meetings_by_app: dict
    trend: List[dict]  # Daily/weekly counts


class TopicStats(BaseModel):
    """Topic analysis statistics."""
    total_topics: int
    top_topics: List[dict]
    topic_trends: List[dict]
    emerging_topics: List[dict]


class ActionItemStats(BaseModel):
    """Action item statistics."""
    total_created: int
    total_completed: int
    completion_rate: float
    overdue_count: int
    by_priority: dict
    by_status: dict
    completion_trend: List[dict]


class AIUsageStats(BaseModel):
    """AI usage and cost statistics."""
    total_responses: int
    responses_this_period: int
    daily_average: float
    estimated_cost_cents: int
    by_model: dict
    usage_trend: List[dict]


class DashboardOverview(BaseModel):
    """Complete dashboard overview."""
    period: str
    meetings: MeetingStats
    topics: TopicStats
    action_items: ActionItemStats
    ai_usage: AIUsageStats
    engagement_score: float


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_date_range(time_range: TimeRange) -> tuple:
    """Get start and end dates for a time range."""
    end_date = datetime.utcnow()

    if time_range == TimeRange.WEEK:
        start_date = end_date - timedelta(days=7)
    elif time_range == TimeRange.MONTH:
        start_date = end_date - timedelta(days=30)
    elif time_range == TimeRange.QUARTER:
        start_date = end_date - timedelta(days=90)
    elif time_range == TimeRange.YEAR:
        start_date = end_date - timedelta(days=365)
    else:  # ALL_TIME
        start_date = datetime(2020, 1, 1)

    return start_date, end_date


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get complete dashboard overview with all metrics.
    """
    start_date, end_date = get_date_range(time_range)

    return DashboardOverview(
        period=time_range.value,
        meetings=_get_meeting_stats(db, user.id, start_date, end_date),
        topics=_get_topic_stats(db, user.id, start_date, end_date),
        action_items=_get_action_item_stats(db, user.id, start_date, end_date),
        ai_usage=_get_ai_usage_stats(db, user.id, start_date, end_date),
        engagement_score=_calculate_engagement_score(db, user.id, start_date, end_date),
    )


@router.get("/meetings", response_model=MeetingStats)
def get_meeting_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed meeting analytics."""
    start_date, end_date = get_date_range(time_range)
    return _get_meeting_stats(db, user.id, start_date, end_date)


@router.get("/topics", response_model=TopicStats)
def get_topic_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed topic analytics."""
    start_date, end_date = get_date_range(time_range)
    return _get_topic_stats(db, user.id, start_date, end_date)


@router.get("/action-items", response_model=ActionItemStats)
def get_action_item_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed action item analytics."""
    start_date, end_date = get_date_range(time_range)
    return _get_action_item_stats(db, user.id, start_date, end_date)


@router.get("/ai-usage", response_model=AIUsageStats)
def get_ai_usage_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI usage and cost analytics."""
    start_date, end_date = get_date_range(time_range)
    return _get_ai_usage_stats(db, user.id, start_date, end_date)


@router.get("/heatmap")
def get_meeting_heatmap(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get meeting frequency heatmap data.

    Returns meeting counts by day of week and hour.
    """
    start_date, end_date = get_date_range(time_range)

    meetings = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date,
        Meeting.started_at <= end_date,
    ).all()

    # Initialize heatmap: day_of_week (0-6) x hour (0-23)
    heatmap = [[0 for _ in range(24)] for _ in range(7)]

    for meeting in meetings:
        if meeting.started_at:
            day = meeting.started_at.weekday()
            hour = meeting.started_at.hour
            heatmap[day][hour] += 1

    return {
        "heatmap": heatmap,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "total_meetings": len(meetings),
    }


@router.get("/productivity-score")
def get_productivity_score(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculate and return productivity score.

    Based on:
    - Action item completion rate
    - Meeting efficiency (summaries generated)
    - AI response utilization
    - Commitment follow-through
    """
    start_date, end_date = get_date_range(time_range)

    # Action item completion
    action_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.created_at >= start_date,
    ).all()

    completed_items = [a for a in action_items if a.status == "completed"]
    completion_rate = len(completed_items) / len(action_items) if action_items else 0

    # Meeting efficiency
    meetings = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date,
        Meeting.status == "ended",
    ).all()

    meetings_with_summary = db.query(MeetingSummary).filter(
        MeetingSummary.user_id == user.id,
        MeetingSummary.created_at >= start_date,
    ).count()

    summary_rate = meetings_with_summary / len(meetings) if meetings else 0

    # Commitment completion
    commitments = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.created_at >= start_date,
    ).all()

    completed_commitments = [c for c in commitments if c.status == "completed"]
    commitment_rate = len(completed_commitments) / len(commitments) if commitments else 0

    # Calculate overall score (0-100)
    score = (
        (completion_rate * 40) +  # 40% weight
        (summary_rate * 30) +     # 30% weight
        (commitment_rate * 30)    # 30% weight
    ) * 100

    return {
        "score": round(score, 1),
        "components": {
            "action_completion": round(completion_rate * 100, 1),
            "meeting_efficiency": round(summary_rate * 100, 1),
            "commitment_rate": round(commitment_rate * 100, 1),
        },
        "trend": "improving",  # TODO: Calculate actual trend
        "period": time_range.value,
    }


@router.get("/export")
def export_analytics(
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    format: str = Query(default="json"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export analytics data.

    Supports JSON and CSV formats.
    """
    start_date, end_date = get_date_range(time_range)

    data = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "range": time_range.value,
        },
        "meetings": _get_meeting_stats(db, user.id, start_date, end_date).model_dump(),
        "topics": _get_topic_stats(db, user.id, start_date, end_date).model_dump(),
        "action_items": _get_action_item_stats(db, user.id, start_date, end_date).model_dump(),
        "ai_usage": _get_ai_usage_stats(db, user.id, start_date, end_date).model_dump(),
        "exported_at": datetime.utcnow().isoformat(),
    }

    if format == "csv":
        # Convert to CSV
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write summary
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Meetings", data["meetings"]["total_meetings"]])
        writer.writerow(["Total Duration (min)", data["meetings"]["total_duration_minutes"]])
        writer.writerow(["AI Responses", data["ai_usage"]["total_responses"]])
        writer.writerow(["Action Items Created", data["action_items"]["total_created"]])
        writer.writerow(["Action Items Completed", data["action_items"]["total_completed"]])

        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics.csv"},
        )

    return data


# =============================================================================
# PRIVATE HELPER FUNCTIONS
# =============================================================================

def _get_meeting_stats(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> MeetingStats:
    """Calculate meeting statistics."""
    meetings = db.query(Meeting).filter(
        Meeting.user_id == user_id,
        Meeting.started_at >= start_date,
        Meeting.started_at <= end_date,
    ).all()

    total_duration = sum(m.duration_seconds or 0 for m in meetings)

    # By type
    by_type = {}
    for m in meetings:
        mt = m.meeting_type or "general"
        by_type[mt] = by_type.get(mt, 0) + 1

    # By app
    by_app = {}
    for m in meetings:
        app = m.meeting_app or "Unknown"
        by_app[app] = by_app.get(app, 0) + 1

    # Daily trend
    trend = []
    current = start_date
    while current <= end_date:
        day_start = current.replace(hour=0, minute=0, second=0)
        day_end = day_start + timedelta(days=1)
        count = sum(1 for m in meetings if day_start <= m.started_at < day_end)
        trend.append({"date": current.strftime("%Y-%m-%d"), "count": count})
        current += timedelta(days=1)

    return MeetingStats(
        total_meetings=len(meetings),
        total_duration_minutes=total_duration // 60,
        avg_duration_minutes=round((total_duration / len(meetings) / 60) if meetings else 0, 1),
        meetings_by_type=by_type,
        meetings_by_app=by_app,
        trend=trend[-30:],  # Last 30 days
    )


def _get_topic_stats(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> TopicStats:
    """Calculate topic statistics."""
    topics = db.query(Topic).filter(
        Topic.user_id == user_id,
    ).order_by(Topic.frequency.desc()).all()

    # Top topics
    top_topics = [
        {"name": t.name, "frequency": t.frequency, "category": t.category}
        for t in topics[:10]
    ]

    # Emerging topics (recently discussed, lower overall frequency)
    recent_topics = db.query(Topic).filter(
        Topic.user_id == user_id,
        Topic.last_discussed >= start_date,
        Topic.frequency < 5,
    ).order_by(Topic.last_discussed.desc()).limit(5).all()

    emerging = [
        {"name": t.name, "frequency": t.frequency, "last_discussed": t.last_discussed.isoformat()}
        for t in recent_topics
    ]

    return TopicStats(
        total_topics=len(topics),
        top_topics=top_topics,
        topic_trends=[],  # TODO: Calculate topic trends over time
        emerging_topics=emerging,
    )


def _get_action_item_stats(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> ActionItemStats:
    """Calculate action item statistics."""
    items = db.query(ActionItem).filter(
        ActionItem.user_id == user_id,
        ActionItem.created_at >= start_date,
    ).all()

    completed = [i for i in items if i.status == "completed"]
    overdue = [i for i in items if i.status != "completed" and i.due_date and i.due_date < datetime.utcnow()]

    # By priority
    by_priority = {}
    for i in items:
        p = i.priority or "medium"
        by_priority[p] = by_priority.get(p, 0) + 1

    # By status
    by_status = {}
    for i in items:
        s = i.status or "pending"
        by_status[s] = by_status.get(s, 0) + 1

    return ActionItemStats(
        total_created=len(items),
        total_completed=len(completed),
        completion_rate=round(len(completed) / len(items) * 100 if items else 0, 1),
        overdue_count=len(overdue),
        by_priority=by_priority,
        by_status=by_status,
        completion_trend=[],  # TODO: Calculate completion trend
    )


def _get_ai_usage_stats(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> AIUsageStats:
    """Calculate AI usage statistics."""
    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == user_id,
        DailyUsage.date >= start_date.date(),
        DailyUsage.date <= end_date.date(),
    ).all()

    total_responses = sum(u.response_count for u in usage)
    days_with_usage = len([u for u in usage if u.response_count > 0])

    # Estimate cost (rough estimate: $0.01 per response)
    estimated_cost = total_responses * 1  # cents

    # Daily trend
    trend = [
        {"date": u.date.isoformat(), "count": u.response_count}
        for u in sorted(usage, key=lambda x: x.date)
    ]

    return AIUsageStats(
        total_responses=total_responses,
        responses_this_period=total_responses,
        daily_average=round(total_responses / days_with_usage if days_with_usage else 0, 1),
        estimated_cost_cents=estimated_cost,
        by_model={"sonnet": total_responses},  # TODO: Track by model
        usage_trend=trend[-30:],
    )


def _calculate_engagement_score(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> float:
    """Calculate user engagement score (0-100)."""
    days = (end_date - start_date).days

    # Count active days
    usage_days = db.query(DailyUsage).filter(
        DailyUsage.user_id == user_id,
        DailyUsage.date >= start_date.date(),
        DailyUsage.response_count > 0,
    ).count()

    meeting_days = db.query(func.distinct(func.date(Meeting.started_at))).filter(
        Meeting.user_id == user_id,
        Meeting.started_at >= start_date,
    ).count()

    active_days = max(usage_days, meeting_days)
    engagement_rate = active_days / days if days > 0 else 0

    return round(min(engagement_rate * 100, 100), 1)
