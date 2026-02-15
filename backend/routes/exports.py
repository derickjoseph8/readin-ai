"""Export API endpoints for multiple formats."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import io

from database import get_db
from models import User, Meeting
from auth import get_current_user
from services.export_service import ExportService, ExportFormat

router = APIRouter(prefix="/export", tags=["Export"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ExportRequest(BaseModel):
    """Request for export operation."""
    meeting_ids: Optional[List[int]] = None
    format: str = "markdown"
    include_conversations: bool = True
    include_action_items: bool = True
    include_summary: bool = True


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/formats")
def list_formats():
    """List available export formats."""
    return {
        "formats": [
            {
                "id": "markdown",
                "name": "Markdown",
                "extension": ".md",
                "description": "Plain text with formatting",
            },
            {
                "id": "json",
                "name": "JSON",
                "extension": ".json",
                "description": "Structured data format",
            },
            {
                "id": "csv",
                "name": "CSV",
                "extension": ".csv",
                "description": "Spreadsheet-compatible",
            },
            {
                "id": "html",
                "name": "HTML",
                "extension": ".html",
                "description": "Web page format",
            },
            {
                "id": "pdf",
                "name": "PDF",
                "extension": ".pdf",
                "description": "Printable document (requires weasyprint)",
            },
            {
                "id": "docx",
                "name": "Word Document",
                "extension": ".docx",
                "description": "Microsoft Word format (requires python-docx)",
            },
        ]
    }


@router.get("/meeting/{meeting_id}")
def export_meeting(
    meeting_id: int,
    format: str = Query(default="markdown", description="Export format"),
    include_conversations: bool = Query(default=True),
    include_action_items: bool = Query(default=True),
    include_summary: bool = Query(default=True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export a single meeting in the specified format.

    Supported formats: markdown, json, csv, html, pdf, docx
    """
    # Verify meeting exists and belongs to user
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id,
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    try:
        export_format = ExportFormat(format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {format}. Supported: markdown, json, csv, html, pdf, docx",
        )

    service = ExportService(db)

    try:
        content, filename, content_type = service.export_meeting(
            meeting,
            export_format,
            include_conversations=include_conversations,
            include_action_items=include_action_items,
            include_summary=include_summary,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )

    return StreamingResponse(
        io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode("utf-8")),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/meetings")
def export_multiple_meetings(
    request: ExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export multiple meetings.

    If meeting_ids is not provided, exports all meetings.
    Bulk export supports: json, csv, markdown
    """
    try:
        export_format = ExportFormat(request.format)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format: {request.format}",
        )

    # Get meetings
    query = db.query(Meeting).filter(Meeting.user_id == user.id)

    if request.meeting_ids:
        query = query.filter(Meeting.id.in_(request.meeting_ids))

    meetings = query.order_by(Meeting.started_at.desc()).limit(500).all()

    if not meetings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No meetings found",
        )

    service = ExportService(db)

    try:
        content, filename, content_type = service.export_multiple_meetings(
            meetings,
            export_format,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return StreamingResponse(
        io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode("utf-8")),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/summary/{meeting_id}")
def export_summary(
    meeting_id: int,
    format: str = Query(default="markdown"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export just the meeting summary.
    """
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == user.id,
    ).first()

    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )

    if not meeting.summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary available for this meeting",
        )

    service = ExportService(db)

    try:
        export_format = ExportFormat(format)
        content, filename, content_type = service.export_meeting(
            meeting,
            export_format,
            include_conversations=False,
            include_action_items=True,
            include_summary=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )

    # Rename file to indicate summary only
    filename = filename.replace(".", "_summary.")

    return StreamingResponse(
        io.BytesIO(content) if isinstance(content, bytes) else io.BytesIO(content.encode("utf-8")),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
