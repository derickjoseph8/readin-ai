"""
Analytics API routes.

Provides:
- User analytics dashboard
- Usage statistics
- Meeting trends
- Topic analysis
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel

from database import get_db
from models import User, Meeting, Conversation, Topic
from auth import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


class UsageStats(BaseModel):
    daily_usage: int
    daily_limit: Optional[int]
    weekly_usage: int
    monthly_usage: int
    total_usage: int


class MeetingTrend(BaseModel):
    date: str
    count: int
    duration_minutes: int


class TopicFrequency(BaseModel):
    topic: str
    count: int
    percentage: float


class ResponseQuality(BaseModel):
    average_rating: float
    total_ratings: int


class AnalyticsDashboard(BaseModel):
    usage: UsageStats
    meeting_trends: List[MeetingTrend]
    top_topics: List[TopicFrequency]
    response_quality: ResponseQuality
    time_saved_minutes: int


@router.get("/dashboard", response_model=AnalyticsDashboard)
def get_analytics_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics dashboard for the current user.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Usage stats
    daily_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= today_start
    ).scalar() or 0

    weekly_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= week_ago
    ).scalar() or 0

    monthly_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= month_ago
    ).scalar() or 0

    total_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id
    ).scalar() or 0

    # Determine daily limit based on subscription
    daily_limit = None
    if user.subscription_status == "free":
        daily_limit = 5
    elif user.subscription_status == "trial":
        daily_limit = 50

    usage_stats = UsageStats(
        daily_usage=daily_count,
        daily_limit=daily_limit,
        weekly_usage=weekly_count,
        monthly_usage=monthly_count,
        total_usage=total_count
    )

    # Meeting trends (last 30 days)
    trends = []
    for i in range(30):
        day = (now - timedelta(days=29-i)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        day_meetings = db.query(
            func.count(Meeting.id),
            func.coalesce(func.sum(Meeting.duration_seconds), 0)
        ).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= day_start,
            Meeting.started_at < day_end
        ).first()

        trends.append(MeetingTrend(
            date=day.isoformat(),
            count=day_meetings[0] or 0,
            duration_minutes=int((day_meetings[1] or 0) / 60)
        ))

    # Top topics
    top_topics = []
    try:
        topic_counts = db.query(
            Topic.name,
            func.count(Topic.id).label('count')
        ).filter(
            Topic.user_id == user.id
        ).group_by(Topic.name).order_by(text('count DESC')).limit(10).all()

        total_topics = sum(t[1] for t in topic_counts) or 1
        for topic_name, count in topic_counts:
            top_topics.append(TopicFrequency(
                topic=topic_name,
                count=count,
                percentage=round((count / total_topics) * 100, 1)
            ))
    except Exception:
        # Topics table might not exist or be empty
        pass

    # Response quality (mock for now, would come from user ratings)
    response_quality = ResponseQuality(
        average_rating=4.2,
        total_ratings=monthly_count if monthly_count > 0 else 0
    )

    # Time saved estimate (30% of meeting time on average)
    total_duration = db.query(func.sum(Meeting.duration_seconds)).filter(
        Meeting.user_id == user.id
    ).scalar() or 0
    time_saved = int((total_duration * 0.3) / 60)  # 30% in minutes

    return AnalyticsDashboard(
        usage=usage_stats,
        meeting_trends=trends,
        top_topics=top_topics,
        response_quality=response_quality,
        time_saved_minutes=time_saved
    )


@router.get("/usage", response_model=UsageStats)
def get_usage_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for the current user.
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    daily_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= today_start
    ).scalar() or 0

    weekly_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= week_ago
    ).scalar() or 0

    monthly_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Conversation.timestamp >= month_ago
    ).scalar() or 0

    total_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id
    ).scalar() or 0

    daily_limit = None
    if user.subscription_status == "free":
        daily_limit = 5
    elif user.subscription_status == "trial":
        daily_limit = 50

    return UsageStats(
        daily_usage=daily_count,
        daily_limit=daily_limit,
        weekly_usage=weekly_count,
        monthly_usage=monthly_count,
        total_usage=total_count
    )


@router.get("/trends", response_model=List[MeetingTrend])
def get_meeting_trends(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get meeting trends for the specified number of days.
    """
    now = datetime.utcnow()
    trends = []

    for i in range(days):
        day = (now - timedelta(days=days-1-i)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        day_meetings = db.query(
            func.count(Meeting.id),
            func.coalesce(func.sum(Meeting.duration_seconds), 0)
        ).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= day_start,
            Meeting.started_at < day_end
        ).first()

        trends.append(MeetingTrend(
            date=day.isoformat(),
            count=day_meetings[0] or 0,
            duration_minutes=int((day_meetings[1] or 0) / 60)
        ))

    return trends


@router.get("/topics", response_model=List[TopicFrequency])
def get_top_topics(
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get top discussion topics.
    """
    try:
        topic_counts = db.query(
            Topic.name,
            func.count(Topic.id).label('count')
        ).filter(
            Topic.user_id == user.id
        ).group_by(Topic.name).order_by(text('count DESC')).limit(limit).all()

        total_topics = sum(t[1] for t in topic_counts) or 1
        topics = []
        for topic_name, count in topic_counts:
            topics.append(TopicFrequency(
                topic=topic_name,
                count=count,
                percentage=round((count / total_topics) * 100, 1)
            ))
        return topics
    except Exception:
        return []


# =============================================================================
# ADVANCED ANALYTICS ENDPOINTS (Phase 8)
# =============================================================================

class MeetingTypeStats(BaseModel):
    """Statistics by meeting type."""
    meeting_type: str
    count: int
    total_duration_minutes: int
    avg_duration_minutes: float
    total_responses: int
    avg_responses_per_meeting: float


class HourlyActivity(BaseModel):
    """Activity by hour of day."""
    hour: int
    meeting_count: int
    response_count: int


class ProductivityInsights(BaseModel):
    """Productivity insights."""
    most_productive_day: Optional[str]
    most_productive_hour: Optional[int]
    avg_meeting_duration_minutes: float
    avg_responses_per_meeting: float
    meetings_with_action_items: int
    total_action_items: int
    completed_action_items: int
    completion_rate: float


class MeetingEffectiveness(BaseModel):
    """Meeting effectiveness metrics."""
    total_meetings: int
    meetings_with_summary: int
    meetings_with_action_items: int
    avg_key_points_per_meeting: float
    summary_coverage_rate: float


class AdvancedAnalytics(BaseModel):
    """Advanced analytics response."""
    meeting_type_stats: List[MeetingTypeStats]
    hourly_activity: List[HourlyActivity]
    productivity_insights: ProductivityInsights
    meeting_effectiveness: MeetingEffectiveness
    response_time_trends: List[dict]


@router.get("/advanced")
def get_advanced_analytics(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get advanced analytics including:
    - Meeting type breakdown
    - Activity by hour
    - Productivity insights
    - Meeting effectiveness metrics
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Meeting type statistics
    meeting_type_stats = []
    type_stats = db.query(
        Meeting.meeting_type,
        func.count(Meeting.id).label('count'),
        func.coalesce(func.sum(Meeting.duration_seconds), 0).label('total_duration'),
        func.coalesce(func.avg(Meeting.duration_seconds), 0).label('avg_duration')
    ).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date
    ).group_by(Meeting.meeting_type).all()

    for stat in type_stats:
        # Get response count for this meeting type
        response_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
            Meeting.user_id == user.id,
            Meeting.meeting_type == stat[0],
            Meeting.started_at >= start_date
        ).scalar() or 0

        meeting_type_stats.append(MeetingTypeStats(
            meeting_type=stat[0] or 'Unknown',
            count=stat[1],
            total_duration_minutes=int(stat[2] / 60),
            avg_duration_minutes=round(stat[3] / 60, 1),
            total_responses=response_count,
            avg_responses_per_meeting=round(response_count / max(stat[1], 1), 1)
        ))

    # Hourly activity
    hourly_activity = []
    for hour in range(24):
        # This is a simplified version - in production, you'd use proper date extraction
        meeting_count = db.query(func.count(Meeting.id)).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start_date,
            func.extract('hour', Meeting.started_at) == hour
        ).scalar() or 0

        response_count = db.query(func.count(Conversation.id)).join(Meeting).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start_date,
            func.extract('hour', Meeting.started_at) == hour
        ).scalar() or 0

        hourly_activity.append(HourlyActivity(
            hour=hour,
            meeting_count=meeting_count,
            response_count=response_count
        ))

    # Find most productive day and hour
    max_meeting_hour = max(hourly_activity, key=lambda x: x.meeting_count, default=None)
    most_productive_hour = max_meeting_hour.hour if max_meeting_hour and max_meeting_hour.meeting_count > 0 else None

    # Day of week stats
    day_stats = {}
    for day_num in range(7):
        count = db.query(func.count(Meeting.id)).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start_date,
            func.extract('dow', Meeting.started_at) == day_num
        ).scalar() or 0
        days_map = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        day_stats[days_map[day_num]] = count

    most_productive_day = max(day_stats, key=day_stats.get) if day_stats else None
    if day_stats.get(most_productive_day, 0) == 0:
        most_productive_day = None

    # Overall stats
    total_meetings = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date
    ).scalar() or 0

    total_responses = db.query(func.count(Conversation.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date
    ).scalar() or 0

    avg_duration = db.query(func.avg(Meeting.duration_seconds)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date,
        Meeting.duration_seconds.isnot(None)
    ).scalar() or 0

    # Meetings with action items
    from models import ActionItem
    meetings_with_actions = db.query(func.count(func.distinct(ActionItem.meeting_id))).join(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date
    ).scalar() or 0

    total_action_items = db.query(func.count(ActionItem.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date
    ).scalar() or 0

    completed_action_items = db.query(func.count(ActionItem.id)).join(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date,
        ActionItem.status == 'completed'
    ).scalar() or 0

    productivity_insights = ProductivityInsights(
        most_productive_day=most_productive_day,
        most_productive_hour=most_productive_hour,
        avg_meeting_duration_minutes=round(avg_duration / 60, 1) if avg_duration else 0,
        avg_responses_per_meeting=round(total_responses / max(total_meetings, 1), 1),
        meetings_with_action_items=meetings_with_actions,
        total_action_items=total_action_items,
        completed_action_items=completed_action_items,
        completion_rate=round(completed_action_items / max(total_action_items, 1) * 100, 1)
    )

    # Meeting effectiveness
    meetings_with_summary = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= start_date,
        Meeting.summary.isnot(None)
    ).scalar() or 0

    # Approximate key points count (assuming key_points is a JSON array)
    avg_key_points = 3.5  # Placeholder - would need proper JSON aggregation

    meeting_effectiveness = MeetingEffectiveness(
        total_meetings=total_meetings,
        meetings_with_summary=meetings_with_summary,
        meetings_with_action_items=meetings_with_actions,
        avg_key_points_per_meeting=avg_key_points,
        summary_coverage_rate=round(meetings_with_summary / max(total_meetings, 1) * 100, 1)
    )

    # Response time trends (average response time by day)
    response_time_trends = []
    for i in range(min(days, 14)):
        day = (now - timedelta(days=13-i)).date()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        avg_response_time = db.query(func.avg(Conversation.response_time_ms)).join(Meeting).filter(
            Meeting.user_id == user.id,
            Conversation.timestamp >= day_start,
            Conversation.timestamp < day_end,
            Conversation.response_time_ms.isnot(None)
        ).scalar()

        response_time_trends.append({
            'date': day.isoformat(),
            'avg_response_time_ms': int(avg_response_time or 0)
        })

    return AdvancedAnalytics(
        meeting_type_stats=meeting_type_stats,
        hourly_activity=hourly_activity,
        productivity_insights=productivity_insights,
        meeting_effectiveness=meeting_effectiveness,
        response_time_trends=response_time_trends
    )


@router.get("/comparison")
def get_period_comparison(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare metrics between current period and previous period.
    Useful for showing growth/decline trends.
    """
    now = datetime.utcnow()
    current_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)
    previous_end = now - timedelta(days=30)

    def get_period_stats(start: datetime, end: datetime):
        meetings = db.query(func.count(Meeting.id)).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start,
            Meeting.started_at < end
        ).scalar() or 0

        responses = db.query(func.count(Conversation.id)).join(Meeting).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start,
            Meeting.started_at < end
        ).scalar() or 0

        duration = db.query(func.sum(Meeting.duration_seconds)).filter(
            Meeting.user_id == user.id,
            Meeting.started_at >= start,
            Meeting.started_at < end
        ).scalar() or 0

        return {
            'meetings': meetings,
            'responses': responses,
            'duration_minutes': int(duration / 60)
        }

    current = get_period_stats(current_start, now)
    previous = get_period_stats(previous_start, previous_end)

    def calculate_change(current_val: int, previous_val: int) -> dict:
        if previous_val == 0:
            return {'value': current_val, 'change': 0, 'trend': 'neutral'}
        change = ((current_val - previous_val) / previous_val) * 100
        trend = 'up' if change > 0 else ('down' if change < 0 else 'neutral')
        return {'value': current_val, 'change': round(change, 1), 'trend': trend}

    return {
        'period': '30 days',
        'meetings': calculate_change(current['meetings'], previous['meetings']),
        'responses': calculate_change(current['responses'], previous['responses']),
        'duration': calculate_change(current['duration_minutes'], previous['duration_minutes']),
    }
