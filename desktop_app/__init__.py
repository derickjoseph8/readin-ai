"""
Desktop App module for ReadIn AI.

Provides offline-first functionality with sync queue:
- OfflineManager: Network connectivity and operation queuing
- LocalStorage: SQLite-based local caching
- EnhancedAPIClient: API client with offline support
- ConflictResolution: Conflict resolution strategies
- SyncOperation: Types of sync operations

Usage:
    from desktop_app import EnhancedAPIClient, get_enhanced_api_client

    # Get global client instance
    api = get_enhanced_api_client()

    # Check connectivity
    if api.is_online:
        result = api.start_meeting(meeting_type="interview", title="Job Interview")
    else:
        # Works offline too - queued for later sync
        result = api.start_meeting(meeting_type="interview", title="Job Interview")
        # result will have offline=True flag

    # Manual sync
    api.sync_now()

    # Get offline status
    status = api.get_offline_status()
"""

from .offline_manager import (
    OfflineManager,
    NetworkStatus,
    OperationType,
    ConflictResolution,
    QueuedOperation,
    SyncResult,
    SyncProgress,
    get_offline_manager,
)

from .local_storage import (
    LocalStorage,
    CachePolicy,
    SyncOperation,
    ConflictStrategy,
    PendingSyncOperation,
    ConflictRecord,
    get_local_storage,
)

from .api_client import (
    EnhancedAPIClient,
    get_enhanced_api_client,
)

__all__ = [
    # Offline Manager
    "OfflineManager",
    "NetworkStatus",
    "OperationType",
    "ConflictResolution",
    "QueuedOperation",
    "SyncResult",
    "SyncProgress",
    "get_offline_manager",
    # Local Storage
    "LocalStorage",
    "CachePolicy",
    "SyncOperation",
    "ConflictStrategy",
    "PendingSyncOperation",
    "ConflictRecord",
    "get_local_storage",
    # Enhanced API Client
    "EnhancedAPIClient",
    "get_enhanced_api_client",
]
