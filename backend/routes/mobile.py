"""
Mobile-optimized API endpoints for React Native mobile app.

Provides bandwidth-efficient endpoints with minimal data payloads:
- Lightweight dashboard data
- Paginated meeting lists with minimal fields
- Quick action item completion
- Push notification management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, Field

from database import get_db
from models import (
    User, Meeting, MeetingSummary, ActionItem, Commitment,
    DeviceToken, Conversation
)
from auth import get_current_user
from schemas import create_pagination_meta, PaginationMeta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["Mobile"])


# =============================================================================
# MOBILE-OPTIMIZED RESPONSE SCHEMAS
# Minimal data for bandwidth efficiency
# =============================================================================

class MobileDashboardStats(BaseModel):
    """Lightweight dashboard statistics for mobile."""
    total_meetings: int = Field(description="Total meeting count")
    meetings_this_week: int = Field(description="Meetings in current week")
    pending_action_items: int = Field(description="Pending action items count")
    overdue_action_items: int = Field(description="Overdue action items count")
    upcoming_commitments: int = Field(description="Commitments due in 7 days")


class MobileActionItemCompact(BaseModel):
    """Compact action item for mobile display."""
    id: int
    description: str = Field(max_length=200)
    due_date: Optional[datetime] = None
    priority: str
    status: str
    is_overdue: bool = False

    class Config:
        from_attributes = True


class MobileCommitmentCompact(BaseModel):
    """Compact commitment for mobile display."""
    id: int
    description: str = Field(max_length=200)
    due_date: Optional[datetime] = None
    status: str
    is_overdue: bool = False

    class Config:
        from_attributes = True


class MobileDashboardResponse(BaseModel):
    """Complete mobile dashboard response."""
    stats: MobileDashboardStats
    recent_action_items: List[MobileActionItemCompact] = Field(
        default_factory=list, max_length=5
    )
    upcoming_commitments: List[MobileCommitmentCompact] = Field(
        default_factory=list, max_length=5
    )
    has_active_meeting: bool = False
    active_meeting_id: Optional[int] = None


class MobileMeetingCompact(BaseModel):
    """Compact meeting data for mobile list view."""
    id: int
    title: Optional[str] = None
    meeting_type: str
    started_at: datetime
    duration_minutes: Optional[int] = None
    status: str
    has_summary: bool = False
    action_item_count: int = 0

    class Config:
        from_attributes = True


class MobileMeetingListResponse(BaseModel):
    """Paginated meeting list for mobile."""
    meetings: List[MobileMeetingCompact]
    meta: PaginationMeta


class MobileSummaryResponse(BaseModel):
    """Meeting summary optimized for mobile viewing."""
    id: int
    meeting_id: int
    meeting_title: Optional[str] = None
    meeting_date: datetime
    summary_text: Optional[str] = None
    key_points: Optional[List[str]] = None
    decisions_made: Optional[List[str]] = None
    action_items_count: int = 0


class MobileNotification(BaseModel):
    """Push notification data structure."""
    id: str
    type: str = Field(description="Notification type: meeting_ended, action_due, commitment_reminder")
    title: str
    body: str
    data: Optional[dict] = None
    created_at: datetime
    is_read: bool = False


class MobileNotificationListResponse(BaseModel):
    """List of notifications for mobile."""
    notifications: List[MobileNotification]
    unread_count: int
    total: int


class MobileDeviceRegisterRequest(BaseModel):
    """Request to register mobile device for push notifications."""
    token: str = Field(..., min_length=10, max_length=500, description="FCM/APNs device token")
    platform: str = Field(..., pattern="^(ios|android)$", description="Mobile platform")
    device_name: Optional[str] = Field(None, max_length=255, description="Device name")
    device_id: Optional[str] = Field(None, max_length=255, description="Unique device identifier")
    app_version: Optional[str] = Field(None, max_length=50, description="App version")
    os_version: Optional[str] = Field(None, max_length=50, description="OS version")


class MobileDeviceRegisterResponse(BaseModel):
    """Response for device registration."""
    id: int
    platform: str
    device_name: Optional[str] = None
    is_active: bool = True
    registered_at: datetime


class MobileActionCompleteResponse(BaseModel):
    """Response for action item completion."""
    success: bool = True
    action_item_id: int
    completed_at: datetime
    remaining_pending: int = Field(description="Remaining pending action items")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/dashboard", response_model=MobileDashboardResponse)
async def get_mobile_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lightweight dashboard data optimized for mobile.

    Returns minimal data including:
    - Key statistics
    - Top 5 recent action items
    - Top 5 upcoming commitments
    - Active meeting status
    """
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    week_ahead = now + timedelta(days=7)

    # Get stats with efficient queries
    total_meetings = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id
    ).scalar() or 0

    meetings_this_week = db.query(func.count(Meeting.id)).filter(
        Meeting.user_id == user.id,
        Meeting.started_at >= week_ago
    ).scalar() or 0

    pending_action_items = db.query(func.count(ActionItem.id)).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending"
    ).scalar() or 0

    overdue_action_items = db.query(func.count(ActionItem.id)).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending",
        ActionItem.due_date.isnot(None),
        ActionItem.due_date < now
    ).scalar() or 0

    upcoming_commitments = db.query(func.count(Commitment.id)).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date <= week_ahead,
        Commitment.due_date >= now
    ).scalar() or 0

    # Get recent action items (limit 5 for mobile)
    recent_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status.in_(["pending", "in_progress"])
    ).order_by(
        ActionItem.due_date.asc().nullslast(),
        desc(ActionItem.created_at)
    ).limit(5).all()

    action_items_compact = [
        MobileActionItemCompact(
            id=item.id,
            description=item.description[:200] if item.description else "",
            due_date=item.due_date,
            priority=item.priority or "medium",
            status=item.status or "pending",
            is_overdue=bool(item.due_date and item.due_date < now)
        )
        for item in recent_items
    ]

    # Get upcoming commitments (limit 5 for mobile)
    commitments = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending"
    ).order_by(
        Commitment.due_date.asc().nullslast()
    ).limit(5).all()

    commitments_compact = [
        MobileCommitmentCompact(
            id=c.id,
            description=c.description[:200] if c.description else "",
            due_date=c.due_date,
            status=c.status or "pending",
            is_overdue=bool(c.due_date and c.due_date < now)
        )
        for c in commitments
    ]

    # Check for active meeting
    active_meeting = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.status == "active"
    ).order_by(desc(Meeting.started_at)).first()

    return MobileDashboardResponse(
        stats=MobileDashboardStats(
            total_meetings=total_meetings,
            meetings_this_week=meetings_this_week,
            pending_action_items=pending_action_items,
            overdue_action_items=overdue_action_items,
            upcoming_commitments=upcoming_commitments
        ),
        recent_action_items=action_items_compact,
        upcoming_commitments=commitments_compact,
        has_active_meeting=active_meeting is not None,
        active_meeting_id=active_meeting.id if active_meeting else None
    )


@router.get("/meetings", response_model=MobileMeetingListResponse)
async def get_mobile_meetings(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=50, description="Items per page (max 50)"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    meeting_type: Optional[str] = Query(default=None, description="Filter by type"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get paginated meeting list with minimal fields for mobile.

    Optimized for:
    - Smaller payload size
    - Fast scrolling/pagination
    - Offline caching
    """
    query = db.query(Meeting).filter(Meeting.user_id == user.id)

    # Apply filters
    if status:
        query = query.filter(Meeting.status == status)
    if meeting_type:
        query = query.filter(Meeting.meeting_type == meeting_type)

    # Get total count for pagination
    total = query.count()

    # Get paginated meetings
    offset = (page - 1) * page_size
    meetings = query.order_by(
        desc(Meeting.started_at)
    ).offset(offset).limit(page_size).all()

    # Get meeting IDs for batch queries
    meeting_ids = [m.id for m in meetings]

    # Batch query for summaries (just check existence)
    summaries_exist = set()
    if meeting_ids:
        summary_ids = db.query(MeetingSummary.meeting_id).filter(
            MeetingSummary.meeting_id.in_(meeting_ids)
        ).all()
        summaries_exist = {s[0] for s in summary_ids}

    # Batch query for action item counts
    action_counts = {}
    if meeting_ids:
        counts = db.query(
            ActionItem.meeting_id,
            func.count(ActionItem.id)
        ).filter(
            ActionItem.meeting_id.in_(meeting_ids)
        ).group_by(ActionItem.meeting_id).all()
        action_counts = dict(counts)

    # Build compact response
    meetings_compact = [
        MobileMeetingCompact(
            id=m.id,
            title=m.title[:100] if m.title else None,
            meeting_type=m.meeting_type or "general",
            started_at=m.started_at,
            duration_minutes=m.duration_seconds // 60 if m.duration_seconds else None,
            status=m.status or "ended",
            has_summary=m.id in summaries_exist,
            action_item_count=action_counts.get(m.id, 0)
        )
        for m in meetings
    ]

    return MobileMeetingListResponse(
        meetings=meetings_compact,
        meta=create_pagination_meta(page, page_size, total)
    )


@router.get("/meetings/{meeting_id}/summary", response_model=MobileSummaryResponse)
async def get_mobile_meeting_summary(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get meeting summary optimized for mobile viewing.

    Returns only essential summary data:
    - Summary text
    - Key points (list)
    - Decisions made (list)
    - Action items count
    """
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

    # Get summary
    summary = db.query(MeetingSummary).filter(
        MeetingSummary.meeting_id == meeting_id
    ).first()

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not yet generated for this meeting"
        )

    # Get action items count
    action_count = db.query(func.count(ActionItem.id)).filter(
        ActionItem.meeting_id == meeting_id
    ).scalar() or 0

    # Parse key points and decisions (handle JSON fields)
    key_points = None
    if summary.key_points:
        if isinstance(summary.key_points, list):
            key_points = summary.key_points[:10]  # Limit for mobile
        elif isinstance(summary.key_points, dict):
            key_points = list(summary.key_points.values())[:10]

    decisions = None
    if summary.decisions_made:
        if isinstance(summary.decisions_made, list):
            decisions = summary.decisions_made[:10]
        elif isinstance(summary.decisions_made, dict):
            decisions = list(summary.decisions_made.values())[:10]

    return MobileSummaryResponse(
        id=summary.id,
        meeting_id=meeting_id,
        meeting_title=meeting.title,
        meeting_date=meeting.started_at,
        summary_text=summary.summary_text,
        key_points=key_points,
        decisions_made=decisions,
        action_items_count=action_count
    )


@router.post("/action-items/{item_id}/complete", response_model=MobileActionCompleteResponse)
async def complete_action_item_mobile(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick complete action item endpoint for mobile.

    Optimized for:
    - Single tap completion
    - Minimal request/response
    - Immediate feedback
    """
    action_item = db.query(ActionItem).filter(
        ActionItem.id == item_id,
        ActionItem.user_id == user.id
    ).first()

    if not action_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found"
        )

    if action_item.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action item already completed"
        )

    # Mark as completed
    completed_at = datetime.utcnow()
    action_item.status = "completed"
    action_item.completed_at = completed_at
    db.commit()

    # Get remaining pending count for feedback
    remaining = db.query(func.count(ActionItem.id)).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending"
    ).scalar() or 0

    # Sync to PM tools in background (non-blocking)
    try:
        from services.pm_sync_service import trigger_status_sync
        import asyncio
        asyncio.create_task(trigger_status_sync(db, action_item, "completed"))
    except Exception as e:
        logger.warning(f"Failed to sync action item completion: {e}")

    logger.info(f"Mobile: Action item {item_id} completed by user {user.id}")

    return MobileActionCompleteResponse(
        success=True,
        action_item_id=item_id,
        completed_at=completed_at,
        remaining_pending=remaining
    )


@router.get("/notifications", response_model=MobileNotificationListResponse)
async def get_mobile_notifications(
    limit: int = Query(default=20, ge=1, le=50, description="Max notifications to return"),
    unread_only: bool = Query(default=False, description="Only return unread notifications"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get push notification data for mobile app.

    Returns recent notifications including:
    - Meeting summary ready
    - Action item due reminders
    - Commitment reminders
    - Team activity (if applicable)
    """
    now = datetime.utcnow()
    notifications = []

    # Get recently completed meetings (summaries ready)
    recent_summaries = db.query(MeetingSummary).join(Meeting).filter(
        Meeting.user_id == user.id,
        MeetingSummary.created_at >= now - timedelta(days=7)
    ).order_by(desc(MeetingSummary.created_at)).limit(5).all()

    for summary in recent_summaries:
        notifications.append(MobileNotification(
            id=f"summary_{summary.id}",
            type="meeting_ended",
            title="Meeting Summary Ready",
            body=f"Summary for '{summary.meeting.title or 'Meeting'}' is ready",
            data={"meeting_id": summary.meeting_id, "summary_id": summary.id},
            created_at=summary.created_at,
            is_read=False  # Would track actual read status in production
        ))

    # Get action items due soon or overdue
    due_items = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending",
        ActionItem.due_date.isnot(None),
        ActionItem.due_date <= now + timedelta(days=1)
    ).order_by(ActionItem.due_date).limit(5).all()

    for item in due_items:
        is_overdue = item.due_date < now
        notifications.append(MobileNotification(
            id=f"action_{item.id}",
            type="action_due",
            title="Action Item Due" if not is_overdue else "Action Item Overdue",
            body=item.description[:100] if item.description else "Action item needs attention",
            data={"action_item_id": item.id, "is_overdue": is_overdue},
            created_at=item.due_date,
            is_read=False
        ))

    # Get commitment reminders
    commitment_reminders = db.query(Commitment).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending",
        Commitment.due_date.isnot(None),
        Commitment.due_date <= now + timedelta(days=1)
    ).order_by(Commitment.due_date).limit(5).all()

    for commitment in commitment_reminders:
        is_overdue = commitment.due_date < now
        notifications.append(MobileNotification(
            id=f"commitment_{commitment.id}",
            type="commitment_reminder",
            title="Commitment Reminder" if not is_overdue else "Commitment Overdue",
            body=commitment.description[:100] if commitment.description else "Commitment needs attention",
            data={"commitment_id": commitment.id, "is_overdue": is_overdue},
            created_at=commitment.due_date,
            is_read=False
        ))

    # Sort by date and limit
    notifications.sort(key=lambda x: x.created_at, reverse=True)
    notifications = notifications[:limit]

    # Count unread (all are unread in this simple implementation)
    unread_count = len(notifications)

    return MobileNotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
        total=len(notifications)
    )


@router.post("/device/register", response_model=MobileDeviceRegisterResponse)
async def register_mobile_device(
    request: MobileDeviceRegisterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register mobile device for push notifications.

    Supports iOS (APNs) and Android (FCM) devices.
    If token already exists, updates the device info.
    """
    # Check if token already exists
    existing_token = db.query(DeviceToken).filter(
        DeviceToken.token == request.token
    ).first()

    now = datetime.utcnow()

    if existing_token:
        # Token exists - transfer ownership to current user if different
        if existing_token.user_id != user.id:
            existing_token.user_id = user.id
            logger.info(f"Mobile: Transferred device token to user {user.id}")

        # Update device info
        existing_token.platform = request.platform
        existing_token.device_name = request.device_name
        existing_token.device_id = request.device_id
        existing_token.app_version = request.app_version
        existing_token.os_version = request.os_version
        existing_token.is_active = True
        existing_token.updated_at = now

        db.commit()
        db.refresh(existing_token)

        logger.info(f"Mobile: Updated device registration for user {user.id}")

        return MobileDeviceRegisterResponse(
            id=existing_token.id,
            platform=existing_token.platform,
            device_name=existing_token.device_name,
            is_active=existing_token.is_active,
            registered_at=existing_token.created_at
        )

    # Create new device token
    device_token = DeviceToken(
        user_id=user.id,
        token=request.token,
        platform=request.platform,
        device_name=request.device_name,
        device_id=request.device_id,
        app_version=request.app_version,
        os_version=request.os_version,
        is_active=True,
        created_at=now
    )

    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    logger.info(f"Mobile: Registered new device for user {user.id}, platform: {request.platform}")

    return MobileDeviceRegisterResponse(
        id=device_token.id,
        platform=device_token.platform,
        device_name=device_token.device_name,
        is_active=device_token.is_active,
        registered_at=device_token.created_at
    )


@router.delete("/device/unregister")
async def unregister_mobile_device(
    token: str = Query(..., description="FCM/APNs device token to unregister"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unregister mobile device from push notifications.

    Called when user logs out or disables notifications.
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.token == token,
        DeviceToken.user_id == user.id
    ).first()

    if device:
        db.delete(device)
        db.commit()
        logger.info(f"Mobile: Unregistered device for user {user.id}")

    # Return success even if not found (idempotent)
    return {"success": True, "message": "Device unregistered"}


@router.get("/sync-status")
async def get_mobile_sync_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get sync status for mobile offline support.

    Returns:
    - Last sync timestamps for different data types
    - Pending changes count
    - Server timestamp for sync coordination
    """
    now = datetime.utcnow()

    # Get latest timestamps for different data types
    latest_meeting = db.query(func.max(Meeting.started_at)).filter(
        Meeting.user_id == user.id
    ).scalar()

    latest_action_item = db.query(func.max(ActionItem.created_at)).filter(
        ActionItem.user_id == user.id
    ).scalar()

    latest_commitment = db.query(func.max(Commitment.created_at)).filter(
        Commitment.user_id == user.id
    ).scalar()

    # Count pending items that may need attention
    pending_action_items = db.query(func.count(ActionItem.id)).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending"
    ).scalar() or 0

    pending_commitments = db.query(func.count(Commitment.id)).filter(
        Commitment.user_id == user.id,
        Commitment.status == "pending"
    ).scalar() or 0

    return {
        "server_time": now.isoformat(),
        "last_updates": {
            "meetings": latest_meeting.isoformat() if latest_meeting else None,
            "action_items": latest_action_item.isoformat() if latest_action_item else None,
            "commitments": latest_commitment.isoformat() if latest_commitment else None,
        },
        "pending_counts": {
            "action_items": pending_action_items,
            "commitments": pending_commitments,
        },
        "user_id": user.id,
    }
