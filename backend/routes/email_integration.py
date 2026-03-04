"""Email Integration API Routes - Deep email integration with meetings."""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, EmailMeetingLink
from auth import get_current_user
from services.email_integration_service import EmailIntegrationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email Integration"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class LinkEmailToMeetingRequest(BaseModel):
    """Request to link an email to a meeting."""
    meeting_id: int = Field(..., description="ID of the meeting to link to")
    email_id: str = Field(..., max_length=255, description="External email ID from provider")
    email_subject: str = Field(..., max_length=500, description="Subject line of the email")
    email_from: str = Field(..., max_length=255, description="Sender email address")
    email_body: str = Field(..., max_length=100000, description="Body content of the email")
    email_date: Optional[datetime] = Field(None, description="Date the email was sent")
    email_thread_id: Optional[str] = Field(None, max_length=255, description="Thread ID for conversation tracking")
    email_provider: str = Field(default="generic", max_length=50, description="Email provider (gmail, outlook, etc.)")
    link_type: str = Field(
        default="context",
        pattern="^(context|follow_up|action_required|reference)$",
        description="Type of link"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes about the link")


class LinkEmailResponse(BaseModel):
    """Response for email linking operations."""
    success: bool
    link_id: Optional[int] = None
    message: str
    link: Optional[dict] = None


class CreateTaskFromEmailRequest(BaseModel):
    """Request to extract tasks from an email."""
    email_subject: str = Field(..., max_length=500, description="Subject line of the email")
    email_body: str = Field(..., max_length=100000, description="Body content of the email")
    email_from: str = Field(..., max_length=255, description="Sender email address")
    meeting_id: Optional[int] = Field(None, description="Optional meeting to associate tasks with")
    auto_create: bool = Field(default=False, description="Automatically create extracted tasks")


class TaskExtractionResponse(BaseModel):
    """Response for task extraction from email."""
    success: bool
    message: str
    extracted_tasks: List[dict] = []
    commitments: List[dict] = []
    created_tasks: List[dict] = []
    email_summary: str = ""


class SendSummaryReplyRequest(BaseModel):
    """Request to send meeting summary as email reply."""
    meeting_id: int = Field(..., description="ID of the meeting")
    recipient_email: EmailStr = Field(..., description="Email address to send to")
    include_action_items: bool = Field(default=True, description="Include action items in summary")
    include_commitments: bool = Field(default=True, description="Include commitments in summary")
    custom_message: Optional[str] = Field(None, max_length=2000, description="Custom message to prepend")
    reply_to_email_id: Optional[str] = Field(None, max_length=255, description="Original email ID for threading")


class SendSummaryResponse(BaseModel):
    """Response for sending summary email."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    message_id: Optional[str] = None


class EmailContextResponse(BaseModel):
    """Response containing email context for a meeting."""
    success: bool
    meeting_id: int
    meeting_title: Optional[str] = None
    email_count: int = 0
    emails: List[dict] = []
    emails_by_type: dict = {}
    context_summary: Optional[str] = None
    error: Optional[str] = None


class UnlinkEmailRequest(BaseModel):
    """Request to unlink an email from a meeting."""
    link_id: int = Field(..., description="ID of the email-meeting link to remove")


# =============================================================================
# API ROUTES
# =============================================================================

@router.post("/link-to-meeting", response_model=LinkEmailResponse)
async def link_email_to_meeting(
    data: LinkEmailToMeetingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Link an email to a meeting for context and reference.

    This creates a bidirectional link between an email and a meeting,
    allowing users to:
    - See relevant emails when preparing for meetings
    - Track which emails led to meeting discussions
    - Reference email context during meeting summaries

    Link types:
    - context: Background information for the meeting
    - follow_up: Email requiring follow-up in the meeting
    - action_required: Email containing action items for the meeting
    - reference: General reference material
    """
    service = EmailIntegrationService(db)

    result = await service.link_email_to_meeting(
        user_id=user.id,
        meeting_id=data.meeting_id,
        email_id=data.email_id,
        email_subject=data.email_subject,
        email_from=data.email_from,
        email_body=data.email_body,
        email_date=data.email_date,
        email_thread_id=data.email_thread_id,
        email_provider=data.email_provider,
        link_type=data.link_type,
        notes=data.notes
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to link email to meeting")
        )

    return LinkEmailResponse(**result)


@router.post("/create-task", response_model=TaskExtractionResponse)
async def create_task_from_email(
    data: CreateTaskFromEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract tasks and action items from an email using AI.

    This endpoint analyzes the email content and extracts:
    - Actionable tasks assigned to the user
    - Tasks assigned to others
    - Commitments made by the sender
    - Overall urgency level

    If auto_create is True and a meeting_id is provided,
    the extracted tasks will be automatically created as action items.
    """
    service = EmailIntegrationService(db)

    result = await service.create_task_from_email(
        user_id=user.id,
        email_subject=data.email_subject,
        email_body=data.email_body,
        email_from=data.email_from,
        meeting_id=data.meeting_id,
        auto_create=data.auto_create
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to extract tasks from email")
        )

    return TaskExtractionResponse(**result)


@router.post("/send-summary-reply", response_model=SendSummaryResponse)
async def send_summary_as_reply(
    data: SendSummaryReplyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send meeting summary as an email to participants.

    This allows users to share meeting outcomes with participants
    who may not have access to the ReadIn AI platform.

    The email includes:
    - Meeting summary text
    - Key discussion points
    - Action items (if enabled)
    - Commitments (if enabled)
    - Link to view full details (for ReadIn users)
    """
    service = EmailIntegrationService(db)

    result = await service.send_summary_as_reply(
        user_id=user.id,
        meeting_id=data.meeting_id,
        recipient_email=data.recipient_email,
        include_action_items=data.include_action_items,
        include_commitments=data.include_commitments,
        custom_message=data.custom_message,
        reply_to_email_id=data.reply_to_email_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to send summary email")
        )

    return SendSummaryResponse(
        success=True,
        message="Meeting summary sent successfully",
        message_id=result.get("message_id")
    )


@router.get("/meeting-context/{meeting_id}", response_model=EmailContextResponse)
async def get_email_context_for_meeting(
    meeting_id: int,
    include_body: bool = True,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all email context linked to a meeting.

    Returns all emails that have been linked to the specified meeting,
    organized by link type with an AI-generated context summary.

    This is useful for:
    - Pre-meeting preparation
    - Understanding discussion context
    - Reviewing relevant correspondence

    Query Parameters:
    - include_body: Whether to include full email bodies (default: true)
    - limit: Maximum number of emails to return (default: 20, max: 50)
    """
    if limit > 50:
        limit = 50

    service = EmailIntegrationService(db)

    result = await service.get_email_context_for_meeting(
        user_id=user.id,
        meeting_id=meeting_id,
        include_body=include_body,
        limit=limit
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Meeting not found")
        )

    return EmailContextResponse(**result)


@router.delete("/unlink/{link_id}")
async def unlink_email_from_meeting(
    link_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an email-meeting link.

    This does not delete the email or the meeting, just the
    association between them.
    """
    service = EmailIntegrationService(db)

    result = await service.unlink_email_from_meeting(
        user_id=user.id,
        link_id=link_id
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Link not found")
        )

    return {"message": "Email unlinked from meeting successfully"}


@router.get("/linked-meetings")
async def get_emails_linked_to_meetings(
    email_id: Optional[str] = None,
    email_provider: Optional[str] = None,
    link_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all email-meeting links for the current user.

    Useful for finding which meetings an email is linked to,
    or browsing all email integrations.

    Query Parameters:
    - email_id: Filter by specific email ID
    - email_provider: Filter by email provider (gmail, outlook, etc.)
    - link_type: Filter by link type (context, follow_up, action_required, reference)
    - skip: Pagination offset
    - limit: Maximum results (default: 50, max: 100)
    """
    if limit > 100:
        limit = 100

    query = db.query(EmailMeetingLink).filter(
        EmailMeetingLink.user_id == user.id
    )

    if email_id:
        query = query.filter(EmailMeetingLink.email_id == email_id)
    if email_provider:
        query = query.filter(EmailMeetingLink.email_provider == email_provider)
    if link_type:
        query = query.filter(EmailMeetingLink.link_type == link_type)

    total = query.count()
    links = query.order_by(EmailMeetingLink.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "links": [
            {
                "id": link.id,
                "meeting_id": link.meeting_id,
                "email_id": link.email_id,
                "email_subject": link.email_subject,
                "email_from": link.email_from,
                "email_date": link.email_date.isoformat() if link.email_date else None,
                "email_provider": link.email_provider,
                "link_type": link.link_type,
                "notes": link.notes,
                "created_at": link.created_at.isoformat() if link.created_at else None
            }
            for link in links
        ]
    }
