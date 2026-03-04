"""
Service layer for ReadIn AI Desktop App.

Provides clean abstractions for:
- Meeting lifecycle management
- Audio capture and transcription
- AI response generation
- Backend synchronization
- Speaker diarization
"""

from .meeting_service import MeetingService
from .audio_service import AudioService
from .transcription_service import TranscriptionService
from .ai_service import AIService
from .sync_service import SyncService
from .speaker_diarization import (
    SpeakerDiarizer,
    SpeakerSegment,
    DiarizationResult,
    DiarizedTranscriber,
)

__all__ = [
    "MeetingService",
    "AudioService",
    "TranscriptionService",
    "AIService",
    "SyncService",
    "SpeakerDiarizer",
    "SpeakerSegment",
    "DiarizationResult",
    "DiarizedTranscriber",
]
