"""
Collaboration API routes.

Endpoints for shared notes, comments, @mentions, and meeting handoffs.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from routes.auth import get_current_user
from models import User, SharedNote, NoteComment, MeetingHandoff
from database import get_db
from sqlalchemy.orm import Session
from services.collaboration_service import CollaborationService

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# Request/Response Models
class CreateNoteRequest(BaseModel):
    content: str = ""


class UpdateNoteRequest(BaseModel):
    content: str


class NoteResponse(BaseModel):
    id: str
    meeting_id: str
    content: str
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CreateCommentRequest(BaseModel):
    content: str
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    id: str
    note_id: str
    user_id: str
    content: str
    mentions: List[str]
    parent_id: Optional[str] = None
    created_at: datetime


class CreateHandoffRequest(BaseModel):
    to_user_id: str
    notes: Optional[str] = None


class HandoffResponse(BaseModel):
    id: str
    meeting_id: str
    from_user_id: str
    to_user_id: str
    notes: Optional[str]
    status: str
    created_at: datetime


class RespondHandoffRequest(BaseModel):
    accept: bool


# Shared Notes Endpoints
@router.post("/meetings/{meeting_id}/notes", response_model=NoteResponse)
async def create_note(
    meeting_id: str,
    request: CreateNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a shared note for a meeting."""
    service = CollaborationService(db)

    result = await service.create_shared_note(
        meeting_id=UUID(meeting_id),
        created_by=current_user.id,
        content=request.content,
        organization_id=current_user.organization_id
    )

    return NoteResponse(**result)


@router.get("/meetings/{meeting_id}/notes", response_model=List[NoteResponse])
async def get_meeting_notes(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all shared notes for a meeting."""
    notes = db.query(SharedNote).filter(
        SharedNote.meeting_id == UUID(meeting_id)
    ).order_by(SharedNote.created_at.desc()).all()

    return [
        NoteResponse(
            id=str(n.id),
            meeting_id=str(n.meeting_id),
            content=n.content,
            created_by=str(n.created_by),
            created_at=n.created_at,
            updated_at=n.updated_at
        )
        for n in notes
    ]


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a shared note."""
    service = CollaborationService(db)

    result = await service.update_note(
        note_id=UUID(note_id),
        content=request.content,
        updated_by=current_user.id
    )

    note = db.query(SharedNote).filter(SharedNote.id == UUID(note_id)).first()

    return NoteResponse(
        id=str(note.id),
        meeting_id=str(note.meeting_id),
        content=note.content,
        created_by=str(note.created_by),
        created_at=note.created_at,
        updated_at=note.updated_at
    )


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a shared note."""
    note = db.query(SharedNote).filter(SharedNote.id == UUID(note_id)).first()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(note)
    db.commit()

    return {"deleted": True}


# Comments Endpoints
@router.post("/notes/{note_id}/comments", response_model=CommentResponse)
async def add_comment(
    note_id: str,
    request: CreateCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a comment to a shared note."""
    service = CollaborationService(db)

    parent_id = UUID(request.parent_id) if request.parent_id else None

    result = await service.add_comment(
        note_id=UUID(note_id),
        user_id=current_user.id,
        content=request.content,
        parent_id=parent_id
    )

    return CommentResponse(**result)


@router.get("/notes/{note_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all comments for a note."""
    comments = db.query(NoteComment).filter(
        NoteComment.note_id == UUID(note_id)
    ).order_by(NoteComment.created_at).all()

    return [
        CommentResponse(
            id=str(c.id),
            note_id=str(c.note_id),
            user_id=str(c.user_id),
            content=c.content,
            mentions=c.mentions or [],
            parent_id=str(c.parent_id) if c.parent_id else None,
            created_at=c.created_at
        )
        for c in comments
    ]


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a comment."""
    comment = db.query(NoteComment).filter(
        NoteComment.id == UUID(comment_id)
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(comment)
    db.commit()

    return {"deleted": True}


# Meeting Handoff Endpoints
@router.post("/meetings/{meeting_id}/handoff", response_model=HandoffResponse)
async def create_handoff(
    meeting_id: str,
    request: CreateHandoffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a meeting handoff request."""
    service = CollaborationService(db)

    result = await service.create_handoff(
        meeting_id=UUID(meeting_id),
        from_user_id=current_user.id,
        to_user_id=UUID(request.to_user_id),
        notes=request.notes
    )

    return HandoffResponse(**result)


@router.get("/handoffs", response_model=List[HandoffResponse])
async def get_my_handoffs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get handoff requests for current user."""
    handoffs = db.query(MeetingHandoff).filter(
        (MeetingHandoff.to_user_id == current_user.id) |
        (MeetingHandoff.from_user_id == current_user.id)
    ).order_by(MeetingHandoff.created_at.desc()).all()

    return [
        HandoffResponse(
            id=str(h.id),
            meeting_id=str(h.meeting_id),
            from_user_id=str(h.from_user_id),
            to_user_id=str(h.to_user_id),
            notes=h.notes,
            status=h.status,
            created_at=h.created_at
        )
        for h in handoffs
    ]


@router.put("/handoffs/{handoff_id}", response_model=HandoffResponse)
async def respond_to_handoff(
    handoff_id: str,
    request: RespondHandoffRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or decline a handoff request."""
    service = CollaborationService(db)

    try:
        result = await service.respond_to_handoff(
            handoff_id=UUID(handoff_id),
            user_id=current_user.id,
            accept=request.accept
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    handoff = db.query(MeetingHandoff).filter(
        MeetingHandoff.id == UUID(handoff_id)
    ).first()

    return HandoffResponse(
        id=str(handoff.id),
        meeting_id=str(handoff.meeting_id),
        from_user_id=str(handoff.from_user_id),
        to_user_id=str(handoff.to_user_id),
        notes=handoff.notes,
        status=handoff.status,
        created_at=handoff.created_at
    )
