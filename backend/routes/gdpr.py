"""
GDPR compliance API routes.

Provides data subject rights:
- Data export
- Account deletion
- Consent management
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from database import get_db
from models import (
    User, Meeting, Conversation, MeetingSummary, ActionItem,
    Commitment, Topic, ParticipantMemory, UserLearningProfile,
    PreMeetingBriefing, AuditLog
)
from auth import get_current_user

router = APIRouter(prefix="/gdpr", tags=["GDPR"])


class ConsentSettings(BaseModel):
    """User consent preferences."""
    consent_analytics: bool = False
    consent_marketing: bool = False
    consent_ai_training: bool = False


class ExportResponse(BaseModel):
    """Data export response."""
    status: str
    message: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class DeleteResponse(BaseModel):
    """Account deletion response."""
    status: str
    message: str
    scheduled_deletion: Optional[datetime] = None


def log_gdpr_action(
    db: Session,
    user_id: int,
    action: str,
    details: dict = None,
    ip_address: str = None
):
    """Log GDPR-related actions for compliance."""
    audit = AuditLog(
        user_id=user_id,
        action=f"gdpr_{action}",
        resource_type="user",
        resource_id=user_id,
        ip_address=ip_address,
        details=details or {}
    )
    db.add(audit)
    db.commit()


@router.get("/consents", response_model=ConsentSettings)
def get_consents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current consent settings for the user.

    GDPR Article 7: Conditions for consent
    """
    return ConsentSettings(
        consent_analytics=user.consent_analytics or False,
        consent_marketing=user.consent_marketing or False,
        consent_ai_training=user.consent_ai_training or False
    )


@router.put("/consents", response_model=ConsentSettings)
def update_consents(
    consents: ConsentSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update consent settings.

    GDPR Article 7: Users can withdraw consent at any time.
    """
    # Track what changed for audit
    changes = {}
    if user.consent_analytics != consents.consent_analytics:
        changes["consent_analytics"] = {
            "from": user.consent_analytics,
            "to": consents.consent_analytics
        }
    if user.consent_marketing != consents.consent_marketing:
        changes["consent_marketing"] = {
            "from": user.consent_marketing,
            "to": consents.consent_marketing
        }
    if user.consent_ai_training != consents.consent_ai_training:
        changes["consent_ai_training"] = {
            "from": user.consent_ai_training,
            "to": consents.consent_ai_training
        }

    # Update consents
    user.consent_analytics = consents.consent_analytics
    user.consent_marketing = consents.consent_marketing
    user.consent_ai_training = consents.consent_ai_training
    user.consent_updated_at = datetime.utcnow()

    db.commit()

    # Log the change
    log_gdpr_action(db, user.id, "consent_update", {"changes": changes})

    return consents


@router.post("/export", response_model=ExportResponse)
def request_data_export(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request export of all user data.

    GDPR Article 20: Right to data portability
    Returns all user data in JSON format.
    """
    # Log the export request
    log_gdpr_action(db, user.id, "export_request", {})

    # Collect all user data
    export_data = _collect_user_data(db, user.id)

    # In production, this would be stored and a download link provided
    # For now, we'll return the data directly (small datasets)
    # TODO: For large datasets, use background task and email download link

    return ExportResponse(
        status="completed",
        message="Your data export is ready. In production, a download link would be emailed.",
        download_url=None,
        expires_at=None
    )


@router.get("/export/data")
def download_data_export(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download user data export as JSON.

    GDPR Article 20: Data must be in structured, machine-readable format.
    """
    export_data = _collect_user_data(db, user.id)

    # Log the download
    log_gdpr_action(db, user.id, "export_download", {"size_bytes": len(json.dumps(export_data))})

    return {
        "export_date": datetime.utcnow().isoformat(),
        "user_id": user.id,
        "format": "JSON",
        "data": export_data
    }


def _collect_user_data(db: Session, user_id: int) -> dict:
    """Collect all user data for export."""
    user = db.query(User).filter(User.id == user_id).first()

    # User profile
    profile = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "profession_id": user.profession_id,
        "specialization": user.specialization,
        "years_experience": user.years_experience,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "subscription_status": user.subscription_status,
        "trial_start": user.trial_start.isoformat() if user.trial_start else None,
        "timezone": user.timezone,
        "consents": {
            "analytics": user.consent_analytics,
            "marketing": user.consent_marketing,
            "ai_training": user.consent_ai_training,
            "updated_at": user.consent_updated_at.isoformat() if user.consent_updated_at else None
        }
    }

    # Meetings
    meetings = db.query(Meeting).filter(Meeting.user_id == user_id).all()
    meetings_data = []
    for m in meetings:
        meeting_data = {
            "id": m.id,
            "meeting_type": m.meeting_type,
            "title": m.title,
            "meeting_app": m.meeting_app,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "ended_at": m.ended_at.isoformat() if m.ended_at else None,
            "duration_seconds": m.duration_seconds,
            "status": m.status,
            "participant_count": m.participant_count,
            "notes": m.notes,
        }

        # Conversations for this meeting
        convs = db.query(Conversation).filter(Conversation.meeting_id == m.id).all()
        meeting_data["conversations"] = [
            {
                "id": c.id,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "speaker": c.speaker,
                "content": c.content,
                "ai_response": c.ai_response,
            }
            for c in convs
        ]

        meetings_data.append(meeting_data)

    # Action items
    action_items = db.query(ActionItem).filter(ActionItem.user_id == user_id).all()
    action_items_data = [
        {
            "id": a.id,
            "meeting_id": a.meeting_id,
            "description": a.description,
            "assignee": a.assignee,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "status": a.status,
            "priority": a.priority,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in action_items
    ]

    # Learning profile
    profile_data = db.query(UserLearningProfile).filter(UserLearningProfile.user_id == user_id).first()
    learning_profile_data = None
    if profile_data:
        learning_profile_data = {
            "id": profile_data.id,
            "formality_level": profile_data.formality_level,
            "verbosity": profile_data.verbosity,
            "technical_depth": profile_data.technical_depth,
            "frequent_topics": profile_data.frequent_topics,
            "topic_expertise": profile_data.topic_expertise,
            "preferred_response_length": profile_data.preferred_response_length,
            "total_conversations_analyzed": profile_data.total_conversations_analyzed,
            "confidence_score": profile_data.confidence_score,
            "updated_at": profile_data.updated_at.isoformat() if profile_data.updated_at else None,
        }

    # Participant memories
    memories = db.query(ParticipantMemory).filter(ParticipantMemory.user_id == user_id).all()
    participant_memories_data = [
        {
            "id": pm.id,
            "participant_name": pm.participant_name,
            "relationship": pm.relationship,
            "notes": pm.notes,
            "last_meeting": pm.last_meeting.isoformat() if pm.last_meeting else None,
            "meeting_count": pm.meeting_count,
        }
        for pm in memories
    ]

    # Audit logs (actions user took)
    audits = db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
    audit_data = [
        {
            "action": a.action,
            "resource_type": a.resource_type,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        }
        for a in audits
    ]

    return {
        "profile": profile,
        "meetings": meetings_data,
        "action_items": action_items_data,
        "learning_profile": learning_profile_data,
        "participant_memories": participant_memories_data,
        "audit_log": audit_data,
    }


@router.post("/delete", response_model=DeleteResponse)
def request_account_deletion(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request account and data deletion.

    GDPR Article 17: Right to erasure ("right to be forgotten")

    This schedules the account for deletion. The user has 30 days
    to cancel the request by logging in again.
    """
    # Schedule deletion (30 day grace period)
    from datetime import timedelta
    scheduled_date = datetime.utcnow() + timedelta(days=30)

    user.deletion_requested = True
    user.deletion_scheduled = scheduled_date
    db.commit()

    # Log the request
    log_gdpr_action(db, user.id, "deletion_request", {
        "scheduled_for": scheduled_date.isoformat()
    })

    # TODO: Send confirmation email
    # background_tasks.add_task(send_deletion_confirmation_email, user.id)

    return DeleteResponse(
        status="scheduled",
        message="Your account is scheduled for deletion. You have 30 days to cancel by logging in.",
        scheduled_deletion=scheduled_date
    )


@router.post("/delete/cancel", response_model=DeleteResponse)
def cancel_account_deletion(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending account deletion request.
    """
    if not user.deletion_requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No deletion request found"
        )

    user.deletion_requested = False
    user.deletion_scheduled = None
    db.commit()

    # Log the cancellation
    log_gdpr_action(db, user.id, "deletion_cancelled", {})

    return DeleteResponse(
        status="cancelled",
        message="Account deletion has been cancelled.",
        scheduled_deletion=None
    )


@router.delete("/delete/immediate")
def immediate_account_deletion(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Immediately delete account and all data.

    WARNING: This action is irreversible.
    """
    user_id = user.id
    user_email = user.email

    # Log before deletion
    log_gdpr_action(db, user.id, "immediate_deletion", {
        "email": user_email
    })

    # Delete all user data in order (respecting foreign keys)
    db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
    db.query(UserLearningProfile).filter(UserLearningProfile.user_id == user_id).delete()
    db.query(ParticipantMemory).filter(ParticipantMemory.user_id == user_id).delete()
    db.query(PreMeetingBriefing).filter(PreMeetingBriefing.user_id == user_id).delete()
    db.query(ActionItem).filter(ActionItem.user_id == user_id).delete()

    # Delete meetings (cascades to conversations, summaries, etc.)
    meetings = db.query(Meeting).filter(Meeting.user_id == user_id).all()
    for meeting in meetings:
        db.query(Conversation).filter(Conversation.meeting_id == meeting.id).delete()
        db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).delete()
        db.query(Commitment).filter(Commitment.meeting_id == meeting.id).delete()
        db.delete(meeting)

    # Delete user
    db.delete(user)
    db.commit()

    # Clear any cached data
    from cache import cache
    cache.clear_user_cache(user_id)

    return {
        "status": "deleted",
        "message": "Your account and all associated data have been permanently deleted."
    }
