"""
Service layer for ReadIn AI Desktop App.

Provides clean abstractions for:
- Meeting lifecycle management
- Audio capture and transcription
- AI response generation
- Backend synchronization
"""

from .meeting_service import MeetingService
from .audio_service import AudioService
from .transcription_service import TranscriptionService
from .ai_service import AIService
from .sync_service import SyncService

__all__ = [
    "MeetingService",
    "AudioService",
    "TranscriptionService",
    "AIService",
    "SyncService",
]
