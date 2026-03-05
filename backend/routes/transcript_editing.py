"""Transcript Editing API routes for ReadIn AI.

Provides endpoints for:
- Editing transcript text with original preservation
- Reverting edits to original text
- Getting edit history for a meeting
- AI-powered transcription correction suggestions
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from models import User, Conversation, Meeting
from auth import get_current_user
from services.transcript_service import TranscriptService


logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class TranscriptEditRequest(BaseModel):
    """Request schema for editing a transcript."""
    edited_text: str = Field(..., min_length=1, max_length=50000)


class TranscriptRevertResponse(BaseModel):
    """Response schema for reverting a transcript."""
    id: int
    meeting_id: int
    speaker: str
    heard_text: str
    original_text: Optional[str] = None
    is_edited: bool
    reverted_at: datetime

    class Config:
        from_attributes = True


class TranscriptEditResponse(BaseModel):
    """Response schema for an edited transcript."""
    id: int
    meeting_id: int
    speaker: str
    heard_text: str
    response_text: Optional[str] = None
    original_text: Optional[str] = None
    edited_text: Optional[str] = None
    is_edited: bool
    edited_at: Optional[datetime] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class TranscriptChangeEntry(BaseModel):
    """Schema for a single transcript change entry."""
    id: int
    meeting_id: int
    speaker: str
    original_text: Optional[str] = None
    edited_text: Optional[str] = None
    current_text: str
    edited_at: Optional[str] = None
    timestamp: Optional[str] = None


class TranscriptChangesResponse(BaseModel):
    """Response schema for meeting transcript changes."""
    meeting_id: int
    changes: List[TranscriptChangeEntry]
    total_changes: int


class CorrectionEntry(BaseModel):
    """Schema for a single correction suggestion."""
    original: str
    suggested: str
    reason: str
    confidence: float


class CorrectionSuggestionRequest(BaseModel):
    """Request schema for correction suggestion."""
    additional_context: Optional[str] = Field(None, max_length=1000)


class CorrectionSuggestionResponse(BaseModel):
    """Response schema for AI correction suggestions."""
    transcript_id: int
    original_text: str
    corrected_text: str
    corrections: List[CorrectionEntry]
    overall_confidence: float
    notes: Optional[str] = None
    suggested_at: str
    error: Optional[str] = None


class ApplyCorrectionRequest(BaseModel):
    """Request schema for applying a correction suggestion."""
    corrected_text: str = Field(..., min_length=1, max_length=50000)


class TranscriptStatsResponse(BaseModel):
    """Response schema for transcript statistics."""
    meeting_id: int
    total_transcripts: int
    edited_transcripts: int
    unedited_transcripts: int
    edit_percentage: float
    last_edited_at: Optional[str] = None


# =============================================================================
# ROUTER DEFINITION
# =============================================================================

router = APIRouter(tags=["Transcript Editing"])


# =============================================================================
# TRANSCRIPT EDITING ENDPOINTS
# =============================================================================

@router.put("/conversations/{conversation_id}/transcript", response_model=TranscriptEditResponse)
def edit_transcript(
    conversation_id: int,
    data: TranscriptEditRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Edit a transcript line.

    Saves the original text on first edit and tracks edit history.
    The edited text replaces the heard_text while preserving the original.

    Args:
        conversation_id: The ID of the conversation/transcript to edit
        data: The new edited text

    Returns:
        Updated transcript with both original and edited text
    """
    service = TranscriptService(db)

    try:
        conversation = service.edit_transcript(
            conversation_id=conversation_id,
            edited_text=data.edited_text,
            user_id=user.id
        )

        return TranscriptEditResponse(
            id=conversation.id,
            meeting_id=conversation.meeting_id,
            speaker=conversation.speaker,
            heard_text=conversation.heard_text,
            response_text=conversation.response_text,
            original_text=conversation.original_text,
            edited_text=conversation.edited_text,
            is_edited=conversation.is_edited,
            edited_at=conversation.edited_at,
            timestamp=conversation.timestamp
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to edit transcript {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit transcript"
        )


@router.post("/conversations/{conversation_id}/revert", response_model=TranscriptRevertResponse)
def revert_transcript(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revert a transcript to its original text.

    Restores the original transcription before any edits were made.
    The original text is preserved even after reverting for reference.

    Args:
        conversation_id: The ID of the conversation/transcript to revert

    Returns:
        Reverted transcript with original text restored
    """
    service = TranscriptService(db)

    try:
        conversation = service.revert_transcript(
            conversation_id=conversation_id,
            user_id=user.id
        )

        return TranscriptRevertResponse(
            id=conversation.id,
            meeting_id=conversation.meeting_id,
            speaker=conversation.speaker,
            heard_text=conversation.heard_text,
            original_text=conversation.original_text,
            is_edited=conversation.is_edited,
            reverted_at=datetime.utcnow()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to revert transcript {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revert transcript"
        )


@router.get("/meetings/{meeting_id}/transcript/changes", response_model=TranscriptChangesResponse)
def get_transcript_changes(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all transcript edits for a meeting.

    Returns a list of all edited transcripts showing both original
    and edited text for comparison and tracking.

    Args:
        meeting_id: The ID of the meeting to get changes for

    Returns:
        List of all edited transcripts with change details
    """
    service = TranscriptService(db)

    try:
        changes = service.get_meeting_transcript_changes(
            meeting_id=meeting_id,
            user_id=user.id
        )

        return TranscriptChangesResponse(
            meeting_id=meeting_id,
            changes=[TranscriptChangeEntry(**change) for change in changes],
            total_changes=len(changes)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get transcript changes for meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transcript changes"
        )


@router.post(
    "/conversations/{conversation_id}/suggest-correction",
    response_model=CorrectionSuggestionResponse
)
async def suggest_transcript_correction(
    conversation_id: int,
    data: Optional[CorrectionSuggestionRequest] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-powered correction suggestions for a transcript.

    Uses Claude AI to analyze the transcript and suggest corrections
    for common transcription errors including:
    - Misheard words or phrases
    - Technical terminology
    - Proper nouns
    - Grammar and punctuation issues

    Args:
        conversation_id: The ID of the conversation/transcript to analyze
        data: Optional additional context to help the AI

    Returns:
        AI-suggested corrections with confidence scores
    """
    service = TranscriptService(db)

    try:
        additional_context = data.additional_context if data else None

        result = await service.suggest_correction(
            conversation_id=conversation_id,
            user_id=user.id,
            additional_context=additional_context
        )

        # Convert corrections to proper schema
        corrections = [
            CorrectionEntry(
                original=c.get("original", ""),
                suggested=c.get("suggested", ""),
                reason=c.get("reason", ""),
                confidence=c.get("confidence", 0.0)
            )
            for c in result.get("corrections", [])
        ]

        return CorrectionSuggestionResponse(
            transcript_id=result["transcript_id"],
            original_text=result["original_text"],
            corrected_text=result["corrected_text"],
            corrections=corrections,
            overall_confidence=result.get("overall_confidence", 0.0),
            notes=result.get("notes"),
            suggested_at=result.get("suggested_at", datetime.utcnow().isoformat()),
            error=result.get("error")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to generate correction suggestions for {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate correction suggestions"
        )


@router.post(
    "/conversations/{conversation_id}/apply-correction",
    response_model=TranscriptEditResponse
)
def apply_correction(
    conversation_id: int,
    data: ApplyCorrectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply an AI-suggested correction to a transcript.

    This is a convenience endpoint that applies the corrected text
    from the suggest-correction endpoint.

    Args:
        conversation_id: The ID of the conversation/transcript to update
        data: The corrected text to apply

    Returns:
        Updated transcript with correction applied
    """
    service = TranscriptService(db)

    try:
        conversation = service.apply_correction_suggestion(
            conversation_id=conversation_id,
            corrected_text=data.corrected_text,
            user_id=user.id
        )

        return TranscriptEditResponse(
            id=conversation.id,
            meeting_id=conversation.meeting_id,
            speaker=conversation.speaker,
            heard_text=conversation.heard_text,
            response_text=conversation.response_text,
            original_text=conversation.original_text,
            edited_text=conversation.edited_text,
            is_edited=conversation.is_edited,
            edited_at=conversation.edited_at,
            timestamp=conversation.timestamp
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to apply correction for {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply correction"
        )


@router.get("/meetings/{meeting_id}/transcript/stats", response_model=TranscriptStatsResponse)
def get_transcript_stats(
    meeting_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about transcript edits for a meeting.

    Returns counts and percentages of edited vs unedited transcripts.

    Args:
        meeting_id: The ID of the meeting to get stats for

    Returns:
        Statistics about transcript edits
    """
    service = TranscriptService(db)

    try:
        stats = service.get_transcript_stats(
            meeting_id=meeting_id,
            user_id=user.id
        )

        return TranscriptStatsResponse(**stats)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get transcript stats for meeting {meeting_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get transcript stats"
        )
