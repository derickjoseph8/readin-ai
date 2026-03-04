"""
Service layer for ReadIn AI Desktop App.

Provides clean abstractions for:
- Meeting lifecycle management
- Audio capture and transcription
- AI response generation
- Backend synchronization
- Speaker diarization
- Offline storage and sync
- Real-time translation
"""

from .meeting_service import MeetingService
from .audio_service import AudioService
from .transcription_service import TranscriptionService
from .ai_service import AIService
from .sync_service import SyncService
from .translation_service import TranslationService, TranslationResult, SUPPORTED_LANGUAGES
from .speaker_diarization import (
    SpeakerDiarizer,
    SpeakerSegment,
    DiarizationResult,
    DiarizedTranscriber,
)
from .offline_storage import (
    OfflineStorage,
    SyncStatus,
    EntityType,
    OfflineItem,
    PendingSync,
    get_offline_storage,
)
from .sync_manager import (
    SyncManager,
    ConnectivityStatus,
    ConflictResolution,
    SyncResult,
    SyncProgress,
    get_sync_manager,
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
    # Offline support
    "OfflineStorage",
    "SyncStatus",
    "EntityType",
    "OfflineItem",
    "PendingSync",
    "get_offline_storage",
    "SyncManager",
    "ConnectivityStatus",
    "ConflictResolution",
    "SyncResult",
    "SyncProgress",
    "get_sync_manager",
    # Translation
    "TranslationService",
    "TranslationResult",
    "SUPPORTED_LANGUAGES",
]
