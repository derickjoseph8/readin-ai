"""Bulk operations API endpoints for efficient batch processing."""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User, Meeting, ActionItem, Conversation
from auth import get_current_user
from services.audit_logger import AuditLogger

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


# =============================================================================
# SCHEMAS
# =============================================================================

class BulkDeleteRequest(BaseModel):
    """Request to delete multiple items."""
    ids: List[int] = Field(..., min_length=1, max_length=100, description="IDs to delete (max 100)")


class BulkUpdateStatus(BaseModel):
    """Request to update status of multiple items."""
    ids: List[int] = Field(..., min_length=1, max_length=100)
    status: str = Field(..., description="New status value")


class BulkActionResult(BaseModel):
    """Result of a bulk operation."""
    success_count: int
    failure_count: int
    errors: List[dict] = []


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"


class BulkExportRequest(BaseModel):
    """Request to export multiple items."""
    ids: Optional[List[int]] = Field(default=None, description="Specific IDs to export (all if not provided)")
    format: ExportFormat = Field(default=ExportFormat.JSON)
    include_conversations: bool = Field(default=True, description="Include meeting conversations")
    include_action_items: bool = Field(default=True, description="Include action items")


# =============================================================================
# MEETING BULK OPERATIONS
# =============================================================================

@router.post("/meetings/delete", response_model=BulkActionResult)
def bulk_delete_meetings(
    request: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete multiple meetings.

    Permanently removes meetings and their associated data.
    Limited to 100 items per request.
    """
    success_count = 0
    errors = []

    for meeting_id in request.ids:
        try:
            meeting = db.query(Meeting).filter(
                Meeting.id == meeting_id,
                Meeting.user_id == user.id,
            ).first()

            if not meeting:
                errors.append({
                    "id": meeting_id,
                    "error": "Meeting not found or access denied",
                })
                continue

            db.delete(meeting)
            success_count += 1

        except Exception as e:
            errors.append({
                "id": meeting_id,
                "error": str(e)[:100],
            })

    db.commit()

    # Audit log
    AuditLogger.log(
        db=db,
        action="bulk_delete_meetings",
        user_id=user.id,
        details={
            "requested_ids": request.ids,
            "success_count": success_count,
            "failure_count": len(errors),
        },
    )

    return BulkActionResult(
        success_count=success_count,
        failure_count=len(errors),
        errors=errors,
    )


@router.post("/meetings/export")
def bulk_export_meetings(
    request: BulkExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export multiple meetings.

    Returns meeting data in the requested format.
    """
    query = db.query(Meeting).filter(Meeting.user_id == user.id)

    if request.ids:
        query = query.filter(Meeting.id.in_(request.ids))

    meetings = query.order_by(Meeting.started_at.desc()).limit(1000).all()

    export_data = []
    for meeting in meetings:
        meeting_data = {
            "id": meeting.id,
            "title": meeting.title,
            "meeting_type": meeting.meeting_type,
            "meeting_app": meeting.meeting_app,
            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
            "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
            "duration_seconds": meeting.duration_seconds,
            "status": meeting.status,
            "notes": meeting.notes,
        }

        if request.include_conversations:
            meeting_data["conversations"] = [
                {
                    "id": c.id,
                    "speaker": c.speaker,
                    "heard_text": c.heard_text,
                    "response_text": c.response_text,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                }
                for c in meeting.conversations
            ]

        if request.include_action_items:
            meeting_data["action_items"] = [
                {
                    "id": a.id,
                    "description": a.description,
                    "assignee": a.assignee,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                    "status": a.status,
                    "priority": a.priority,
                }
                for a in meeting.action_items
            ]

        export_data.append(meeting_data)

    # Audit log
    AuditLogger.log(
        db=db,
        action="bulk_export_meetings",
        user_id=user.id,
        details={
            "count": len(export_data),
            "format": request.format,
        },
    )

    if request.format == ExportFormat.CSV:
        # Return CSV format
        import csv
        import io

        output = io.StringIO()
        if export_data:
            writer = csv.DictWriter(output, fieldnames=["id", "title", "meeting_type", "started_at", "status"])
            writer.writeheader()
            for meeting in export_data:
                writer.writerow({
                    "id": meeting["id"],
                    "title": meeting["title"],
                    "meeting_type": meeting["meeting_type"],
                    "started_at": meeting["started_at"],
                    "status": meeting["status"],
                })

        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=meetings.csv"},
        )

    return {
        "meetings": export_data,
        "count": len(export_data),
        "exported_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# ACTION ITEM BULK OPERATIONS
# =============================================================================

@router.post("/tasks/update-status", response_model=BulkActionResult)
def bulk_update_task_status(
    request: BulkUpdateStatus,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update status of multiple action items.

    Valid statuses: pending, in_progress, completed, cancelled
    """
    valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    success_count = 0
    errors = []

    for task_id in request.ids:
        try:
            task = db.query(ActionItem).filter(
                ActionItem.id == task_id,
                ActionItem.user_id == user.id,
            ).first()

            if not task:
                errors.append({
                    "id": task_id,
                    "error": "Task not found or access denied",
                })
                continue

            task.status = request.status
            if request.status == "completed":
                task.completed_at = datetime.utcnow()
            success_count += 1

        except Exception as e:
            errors.append({
                "id": task_id,
                "error": str(e)[:100],
            })

    db.commit()

    return BulkActionResult(
        success_count=success_count,
        failure_count=len(errors),
        errors=errors,
    )


@router.post("/tasks/delete", response_model=BulkActionResult)
def bulk_delete_tasks(
    request: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete multiple action items.
    """
    success_count = 0
    errors = []

    for task_id in request.ids:
        try:
            task = db.query(ActionItem).filter(
                ActionItem.id == task_id,
                ActionItem.user_id == user.id,
            ).first()

            if not task:
                errors.append({
                    "id": task_id,
                    "error": "Task not found or access denied",
                })
                continue

            db.delete(task)
            success_count += 1

        except Exception as e:
            errors.append({
                "id": task_id,
                "error": str(e)[:100],
            })

    db.commit()

    return BulkActionResult(
        success_count=success_count,
        failure_count=len(errors),
        errors=errors,
    )


# =============================================================================
# CONVERSATION BULK OPERATIONS
# =============================================================================

@router.post("/conversations/delete", response_model=BulkActionResult)
def bulk_delete_conversations(
    request: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete multiple conversations.

    Only deletes conversations belonging to user's meetings.
    """
    success_count = 0
    errors = []

    for conv_id in request.ids:
        try:
            conversation = db.query(Conversation).join(Meeting).filter(
                Conversation.id == conv_id,
                Meeting.user_id == user.id,
            ).first()

            if not conversation:
                errors.append({
                    "id": conv_id,
                    "error": "Conversation not found or access denied",
                })
                continue

            db.delete(conversation)
            success_count += 1

        except Exception as e:
            errors.append({
                "id": conv_id,
                "error": str(e)[:100],
            })

    db.commit()

    return BulkActionResult(
        success_count=success_count,
        failure_count=len(errors),
        errors=errors,
    )
