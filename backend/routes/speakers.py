"""Speaker Management API Routes.

Endpoints for managing speaker profiles and diarization.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User
from services.speaker_diarization_service import SpeakerDiarizationService

router = APIRouter(prefix="/speakers", tags=["speakers"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SpeakerCreate(BaseModel):
    """Create speaker request."""
    speaker_id: str = Field(..., description="Speaker identifier (e.g., SPEAKER_00)")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    voice_embedding: Optional[List[float]] = Field(None, description="Voice embedding vector")
    meeting_id: Optional[int] = Field(None, description="Associated meeting")
    speaking_time: float = Field(0.0, ge=0, description="Speaking duration in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SpeakerUpdate(BaseModel):
    """Update speaker request."""
    display_name: Optional[str] = None
    voice_embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class SpeakerRename(BaseModel):
    """Rename speaker request."""
    new_name: str = Field(..., min_length=1, max_length=100)
    update_conversations: bool = Field(True, description="Update all conversation records")


class SpeakerMerge(BaseModel):
    """Merge speakers request."""
    source_speaker_id: str = Field(..., description="Speaker to merge from (will be removed)")
    target_speaker_id: str = Field(..., description="Speaker to merge into")


class VoiceMatch(BaseModel):
    """Voice matching request."""
    voice_embedding: List[float] = Field(..., description="Voice embedding to match")
    threshold: float = Field(0.75, ge=0, le=1, description="Similarity threshold")


class SpeakerResponse(BaseModel):
    """Speaker profile response."""
    id: int
    speaker_id: str
    display_name: str
    total_meetings: Optional[int] = 0
    total_speaking_time: Optional[float] = 0.0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    has_voice_profile: bool = False
    metadata: Optional[Dict[str, Any]] = None


class SpeakerStatsResponse(BaseModel):
    """Speaker statistics response."""
    speaker_id: str
    speaker_name: str
    message_count: int
    character_count: int
    message_percentage: float
    character_percentage: float
    estimated_duration: float


class MeetingSpeakerStatsResponse(BaseModel):
    """Meeting speaker statistics response."""
    total_messages: int
    total_characters: int
    speaker_count: int
    speakers: List[SpeakerStatsResponse]


# =============================================================================
# SPEAKER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[SpeakerResponse])
async def list_speakers(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all known speakers for the current user."""
    service = SpeakerDiarizationService(db)
    speakers = service.get_user_speakers(current_user.id, limit=limit)
    return speakers


@router.post("/", response_model=SpeakerResponse)
async def create_speaker(
    request: SpeakerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update a speaker profile."""
    service = SpeakerDiarizationService(db)
    speaker = service.create_or_update_speaker(
        user_id=current_user.id,
        speaker_id=request.speaker_id,
        display_name=request.display_name,
        voice_embedding=request.voice_embedding,
        meeting_id=request.meeting_id,
        speaking_time=request.speaking_time,
        metadata=request.metadata
    )
    return speaker


@router.get("/meeting/{meeting_id}")
async def get_meeting_speakers(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all speakers detected in a meeting."""
    from models import Meeting

    # Verify meeting ownership
    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = SpeakerDiarizationService(db)
    speakers = service.get_speakers_for_meeting(meeting_id)
    return {"speakers": speakers}


@router.get("/meeting/{meeting_id}/timeline")
async def get_speaker_timeline(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get speaker timeline for a meeting."""
    from models import Meeting

    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = SpeakerDiarizationService(db)
    timeline = service.get_speaker_timeline(meeting_id)
    return {"timeline": timeline}


@router.get("/meeting/{meeting_id}/stats", response_model=MeetingSpeakerStatsResponse)
async def get_meeting_speaker_stats(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get speaker statistics for a meeting."""
    from models import Meeting

    meeting = db.query(Meeting).filter(
        Meeting.id == meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    service = SpeakerDiarizationService(db)
    stats = service.get_speaker_statistics(meeting_id)
    return stats


@router.put("/{speaker_id}/rename")
async def rename_speaker(
    speaker_id: str,
    request: SpeakerRename,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename a speaker."""
    service = SpeakerDiarizationService(db)
    success = service.rename_speaker(
        user_id=current_user.id,
        speaker_id=speaker_id,
        new_name=request.new_name,
        update_conversations=request.update_conversations
    )
    return {"success": success, "speaker_id": speaker_id, "new_name": request.new_name}


@router.post("/merge")
async def merge_speakers(
    request: SpeakerMerge,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Merge two speaker profiles (same person detected as different speakers)."""
    service = SpeakerDiarizationService(db)
    success = service.merge_speakers(
        user_id=current_user.id,
        source_speaker_id=request.source_speaker_id,
        target_speaker_id=request.target_speaker_id
    )
    return {
        "success": success,
        "merged_from": request.source_speaker_id,
        "merged_into": request.target_speaker_id
    }


@router.post("/match")
async def find_matching_speaker(
    request: VoiceMatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find a speaker matching a voice embedding."""
    service = SpeakerDiarizationService(db)
    match = service.find_similar_speaker(
        user_id=current_user.id,
        voice_embedding=request.voice_embedding,
        threshold=request.threshold
    )

    if match:
        return {"found": True, "speaker": match}
    return {"found": False, "speaker": None}


@router.delete("/{speaker_id}")
async def delete_speaker(
    speaker_id: str,
    anonymize: bool = Query(True, description="Anonymize conversations with this speaker"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a speaker profile."""
    service = SpeakerDiarizationService(db)
    success = service.delete_speaker(
        user_id=current_user.id,
        speaker_id=speaker_id,
        anonymize_conversations=anonymize
    )
    return {"success": success, "speaker_id": speaker_id}


# =============================================================================
# CONVERSATION SPEAKER ENDPOINTS
# =============================================================================

@router.put("/conversation/{conversation_id}/speaker")
async def update_conversation_speaker(
    conversation_id: int,
    speaker_id: str = Query(..., description="New speaker ID"),
    speaker_name: Optional[str] = Query(None, description="Speaker display name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the speaker for a specific conversation."""
    from models import Conversation, Meeting

    # Get conversation and verify ownership
    conversation = db.query(Conversation).join(Meeting).filter(
        Conversation.id == conversation_id,
        Meeting.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.speaker_id = speaker_id
    if speaker_name:
        conversation.speaker_name = speaker_name

    db.commit()

    return {
        "success": True,
        "conversation_id": conversation_id,
        "speaker_id": speaker_id,
        "speaker_name": speaker_name
    }


@router.post("/conversation/{conversation_id}/identify")
async def identify_speaker(
    conversation_id: int,
    voice_embedding: List[float],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Identify speaker for a conversation using voice embedding."""
    from models import Conversation, Meeting

    # Get conversation
    conversation = db.query(Conversation).join(Meeting).filter(
        Conversation.id == conversation_id,
        Meeting.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Find matching speaker
    service = SpeakerDiarizationService(db)
    match = service.find_similar_speaker(
        user_id=current_user.id,
        voice_embedding=voice_embedding,
        threshold=0.75
    )

    if match:
        conversation.speaker_id = match["speaker_id"]
        conversation.speaker_name = match["display_name"]
        db.commit()

        return {
            "identified": True,
            "speaker": match,
            "conversation_id": conversation_id
        }

    return {
        "identified": False,
        "speaker": None,
        "conversation_id": conversation_id
    }
