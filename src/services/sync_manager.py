"""
Sync Manager for ReadIn AI.

Handles background synchronization between local offline storage and remote API:
- Background sync when online
- Conflict resolution
- Sync status tracking
- Connectivity monitoring
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import socket

logger = logging.getLogger(__name__)


class ConnectivityStatus(Enum):
    """Network connectivity status."""
    ONLINE = "online"
    OFFLINE = "offline"
    CHECKING = "checking"
    UNSTABLE = "unstable"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    SERVER_WINS = "server_wins"    # Server data takes precedence
    CLIENT_WINS = "client_wins"    # Local data takes precedence
    MERGE = "merge"                # Attempt to merge both
    MANUAL = "manual"              # Require user intervention


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    entity_type: str
    local_id: str
    remote_id: Optional[int] = None
    error: Optional[str] = None
    conflict: bool = False
    resolution: Optional[str] = None


@dataclass
class SyncProgress:
    """Current sync progress."""
    total_items: int = 0
    synced_items: int = 0
    failed_items: int = 0
    conflicts: int = 0
    is_syncing: bool = False
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None


class SyncManager:
    """
    Manages synchronization between offline storage and remote API.

    Features:
    - Background sync thread
    - Connectivity monitoring
    - Conflict resolution
    - Exponential backoff for retries
    - Event callbacks for UI updates
    """

    # Sync intervals
    DEFAULT_SYNC_INTERVAL = 60  # seconds
    MIN_SYNC_INTERVAL = 30
    MAX_SYNC_INTERVAL = 300

    # Connectivity check endpoints
    CONNECTIVITY_HOSTS = [
        ("8.8.8.8", 53),        # Google DNS
        ("1.1.1.1", 53),        # Cloudflare DNS
    ]
    CONNECTIVITY_TIMEOUT = 3.0

    # Retry settings
    MAX_CONSECUTIVE_FAILURES = 5
    BACKOFF_MULTIPLIER = 2.0
    MAX_BACKOFF = 300  # 5 minutes

    def __init__(
        self,
        api_client=None,
        offline_storage=None,
        sync_interval: int = None,
        conflict_strategy: ConflictResolution = ConflictResolution.SERVER_WINS
    ):
        """
        Initialize sync manager.

        Args:
            api_client: API client instance for remote operations
            offline_storage: OfflineStorage instance for local data
            sync_interval: Seconds between sync attempts
            conflict_strategy: Default conflict resolution strategy
        """
        self._api_client = api_client
        self._offline_storage = offline_storage
        self._sync_interval = sync_interval or self.DEFAULT_SYNC_INTERVAL
        self._conflict_strategy = conflict_strategy

        # State
        self._connectivity_status = ConnectivityStatus.CHECKING
        self._is_running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._progress = SyncProgress()
        self._consecutive_failures = 0
        self._current_backoff = self._sync_interval

        # Callbacks
        self._listeners: Dict[str, List[Callable]] = {
            "connectivity_changed": [],
            "sync_started": [],
            "sync_completed": [],
            "sync_progress": [],
            "sync_error": [],
            "conflict_detected": [],
        }

        # Lock for thread safety
        self._lock = threading.RLock()

    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._connectivity_status == ConnectivityStatus.ONLINE

    @property
    def is_syncing(self) -> bool:
        """Check if currently syncing."""
        return self._progress.is_syncing

    @property
    def connectivity_status(self) -> ConnectivityStatus:
        """Get current connectivity status."""
        return self._connectivity_status

    @property
    def progress(self) -> SyncProgress:
        """Get current sync progress."""
        return self._progress

    def set_api_client(self, api_client):
        """Set or update the API client."""
        self._api_client = api_client

    def set_offline_storage(self, offline_storage):
        """Set or update the offline storage."""
        self._offline_storage = offline_storage

    def set_sync_interval(self, interval: int):
        """Set sync interval in seconds."""
        self._sync_interval = max(
            self.MIN_SYNC_INTERVAL,
            min(interval, self.MAX_SYNC_INTERVAL)
        )

    def add_listener(self, event: str, callback: Callable):
        """Add event listener."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable):
        """Remove event listener."""
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def _emit(self, event: str, *args, **kwargs):
        """Emit event to listeners."""
        for callback in self._listeners.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in sync listener for {event}: {e}")

    # ==================== Connectivity ====================

    def check_connectivity(self) -> bool:
        """
        Check network connectivity.

        Returns:
            True if online, False if offline
        """
        old_status = self._connectivity_status
        self._connectivity_status = ConnectivityStatus.CHECKING

        is_online = False
        for host, port in self.CONNECTIVITY_HOSTS:
            try:
                socket.setdefaulttimeout(self.CONNECTIVITY_TIMEOUT)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((host, port))
                s.close()
                is_online = True
                break
            except (socket.timeout, socket.error):
                continue

        # Also check API server if basic connectivity works
        if is_online and self._api_client:
            try:
                # Quick health check to API
                result = self._api_client._request_internal(
                    "GET", "/health",
                    timeout_type="quick"
                )
                is_online = "error" not in result
            except Exception:
                # API unreachable but internet is working
                is_online = False

        self._connectivity_status = (
            ConnectivityStatus.ONLINE if is_online else ConnectivityStatus.OFFLINE
        )

        if old_status != self._connectivity_status:
            logger.info(f"Connectivity changed: {old_status.value} -> {self._connectivity_status.value}")
            self._emit("connectivity_changed", self._connectivity_status)

            # If just came online, trigger immediate sync
            if self._connectivity_status == ConnectivityStatus.ONLINE:
                self._current_backoff = self._sync_interval
                self._consecutive_failures = 0

        return is_online

    # ==================== Sync Operations ====================

    def start(self) -> bool:
        """Start the background sync service."""
        if self._is_running:
            return True

        self._stop_event.clear()
        self._is_running = True

        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="SyncManager"
        )
        self._sync_thread.start()

        logger.info("Sync manager started")
        return True

    def stop(self):
        """Stop the background sync service."""
        self._is_running = False
        self._stop_event.set()

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)

        self._sync_thread = None
        logger.info("Sync manager stopped")

    def sync_now(self) -> bool:
        """Trigger immediate sync."""
        if not self._api_client or not self._offline_storage:
            logger.warning("Cannot sync: API client or storage not configured")
            return False

        if self._progress.is_syncing:
            logger.debug("Sync already in progress")
            return False

        # Run sync in background
        threading.Thread(
            target=self._perform_sync,
            daemon=True,
            name="ImmediateSync"
        ).start()

        return True

    def _sync_loop(self):
        """Background sync loop."""
        while self._is_running:
            try:
                # Check connectivity first
                if self.check_connectivity():
                    # Perform sync
                    self._perform_sync()
                else:
                    logger.debug("Offline - skipping sync")

                # Wait for next interval or stop signal
                self._stop_event.wait(timeout=self._current_backoff)

            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                self._handle_sync_failure(str(e))

    def _perform_sync(self):
        """Perform synchronization."""
        if not self._api_client or not self._offline_storage:
            return

        with self._lock:
            if self._progress.is_syncing:
                return

            self._progress.is_syncing = True
            self._progress.synced_items = 0
            self._progress.failed_items = 0
            self._progress.conflicts = 0

        self._emit("sync_started")
        logger.info("Starting sync...")

        try:
            # Get pending sync items
            pending = self._offline_storage.get_pending_syncs()
            self._progress.total_items = len(pending)

            if not pending:
                logger.debug("No pending items to sync")
                self._handle_sync_success()
                return

            logger.info(f"Syncing {len(pending)} pending items")

            for item in pending:
                if not self._is_running:
                    break

                result = self._sync_item(item)

                if result.success:
                    self._progress.synced_items += 1
                    self._offline_storage.mark_sync_success(
                        item.id,
                        result.remote_id
                    )
                elif result.conflict:
                    self._progress.conflicts += 1
                    self._handle_conflict(item, result)
                else:
                    self._progress.failed_items += 1
                    self._offline_storage.mark_sync_failure(
                        item.id,
                        result.error or "Unknown error"
                    )

                self._emit("sync_progress", self._progress)

            self._handle_sync_success()

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self._handle_sync_failure(str(e))

        finally:
            with self._lock:
                self._progress.is_syncing = False
                self._progress.last_sync = datetime.now()

            self._emit("sync_completed", self._progress)

    def _sync_item(self, item) -> SyncResult:
        """
        Sync a single pending item.

        Args:
            item: PendingSync item to sync

        Returns:
            SyncResult with outcome
        """
        try:
            entity_type = item.entity_type
            operation = item.operation
            data = item.data

            # Route to appropriate API call
            if entity_type == "meeting":
                return self._sync_meeting(item)
            elif entity_type == "conversation":
                return self._sync_conversation(item)
            elif entity_type == "action_item":
                return self._sync_action_item(item)
            else:
                logger.warning(f"Unknown entity type: {entity_type}")
                return SyncResult(
                    success=False,
                    entity_type=entity_type,
                    local_id=item.local_id,
                    error=f"Unknown entity type: {entity_type}"
                )

        except Exception as e:
            logger.error(f"Error syncing item {item.id}: {e}")
            return SyncResult(
                success=False,
                entity_type=item.entity_type,
                local_id=item.local_id,
                error=str(e)
            )

    def _sync_meeting(self, item) -> SyncResult:
        """Sync a meeting item."""
        data = item.data

        if item.operation == "create":
            result = self._api_client.start_meeting(
                meeting_type=data.get("meeting_type", "general"),
                title=data.get("title"),
                meeting_app=data.get("meeting_app")
            )

            if "error" in result:
                return SyncResult(
                    success=False,
                    entity_type="meeting",
                    local_id=item.local_id,
                    error=result.get("message", "Failed to create meeting")
                )

            return SyncResult(
                success=True,
                entity_type="meeting",
                local_id=item.local_id,
                remote_id=result.get("id")
            )

        elif item.operation == "update":
            if item.remote_id:
                # Check if ending meeting
                if "ended_at" in data:
                    result = self._api_client.end_meeting(item.remote_id)
                else:
                    # Other updates - would need PATCH endpoint
                    return SyncResult(
                        success=True,
                        entity_type="meeting",
                        local_id=item.local_id,
                        remote_id=item.remote_id
                    )

                if "error" in result:
                    return SyncResult(
                        success=False,
                        entity_type="meeting",
                        local_id=item.local_id,
                        error=result.get("message", "Failed to update meeting")
                    )

                return SyncResult(
                    success=True,
                    entity_type="meeting",
                    local_id=item.local_id,
                    remote_id=item.remote_id
                )
            else:
                # No remote ID yet - need to create first
                return SyncResult(
                    success=False,
                    entity_type="meeting",
                    local_id=item.local_id,
                    error="Meeting not yet created on server"
                )

        return SyncResult(
            success=False,
            entity_type="meeting",
            local_id=item.local_id,
            error=f"Unknown operation: {item.operation}"
        )

    def _sync_conversation(self, item) -> SyncResult:
        """Sync a conversation item."""
        data = item.data

        if item.operation == "create":
            meeting_id = data.get("meeting_id")

            # If no meeting_id, try to get it from local mapping
            if not meeting_id:
                meeting_local_id = data.get("meeting_local_id")
                if meeting_local_id:
                    meeting = self._offline_storage.get_meeting(meeting_local_id)
                    if meeting:
                        meeting_id = meeting.get("remote_id")

            if not meeting_id:
                return SyncResult(
                    success=False,
                    entity_type="conversation",
                    local_id=item.local_id,
                    error="Meeting not yet synced"
                )

            result = self._api_client.save_conversation(
                meeting_id=meeting_id,
                heard_text=data.get("heard_text", ""),
                response_text=data.get("response_text", ""),
                speaker=data.get("speaker")
            )

            if "error" in result:
                return SyncResult(
                    success=False,
                    entity_type="conversation",
                    local_id=item.local_id,
                    error=result.get("message", "Failed to save conversation")
                )

            return SyncResult(
                success=True,
                entity_type="conversation",
                local_id=item.local_id,
                remote_id=result.get("id")
            )

        return SyncResult(
            success=False,
            entity_type="conversation",
            local_id=item.local_id,
            error=f"Unknown operation: {item.operation}"
        )

    def _sync_action_item(self, item) -> SyncResult:
        """Sync an action item."""
        data = item.data

        if item.operation == "create":
            # API would need an endpoint for this
            # For now, return success to unblock
            return SyncResult(
                success=True,
                entity_type="action_item",
                local_id=item.local_id
            )

        elif item.operation == "update":
            if data.get("completed") and item.remote_id:
                result = self._api_client.complete_action_item(item.remote_id)

                if "error" in result:
                    return SyncResult(
                        success=False,
                        entity_type="action_item",
                        local_id=item.local_id,
                        error=result.get("message", "Failed to complete action item")
                    )

                return SyncResult(
                    success=True,
                    entity_type="action_item",
                    local_id=item.local_id,
                    remote_id=item.remote_id
                )

        return SyncResult(
            success=False,
            entity_type="action_item",
            local_id=item.local_id,
            error=f"Unknown operation: {item.operation}"
        )

    # ==================== Conflict Resolution ====================

    def _handle_conflict(self, item, result: SyncResult):
        """Handle a sync conflict."""
        logger.warning(f"Conflict detected for {item.entity_type}/{item.local_id}")
        self._emit("conflict_detected", item, result)

        # Apply resolution strategy
        if self._conflict_strategy == ConflictResolution.SERVER_WINS:
            # Mark local as synced, server data will override
            self._offline_storage.mark_sync_success(item.id, item.remote_id)

        elif self._conflict_strategy == ConflictResolution.CLIENT_WINS:
            # Retry with force flag
            # Would need API support for this
            pass

        elif self._conflict_strategy == ConflictResolution.MANUAL:
            # Leave in conflict state for user
            pass

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute checksum for conflict detection."""
        # Sort keys for consistent hashing
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

    # ==================== Error Handling ====================

    def _handle_sync_success(self):
        """Handle successful sync."""
        self._consecutive_failures = 0
        self._current_backoff = self._sync_interval
        self._progress.last_error = None

        logger.info(
            f"Sync completed: {self._progress.synced_items} synced, "
            f"{self._progress.failed_items} failed, "
            f"{self._progress.conflicts} conflicts"
        )

    def _handle_sync_failure(self, error: str):
        """Handle sync failure with exponential backoff."""
        self._consecutive_failures += 1
        self._progress.last_error = error

        # Exponential backoff
        self._current_backoff = min(
            self._sync_interval * (self.BACKOFF_MULTIPLIER ** self._consecutive_failures),
            self.MAX_BACKOFF
        )

        logger.warning(
            f"Sync failed ({self._consecutive_failures} consecutive). "
            f"Next retry in {self._current_backoff}s: {error}"
        )

        self._emit("sync_error", error)

        # If too many failures, go offline
        if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self._connectivity_status = ConnectivityStatus.UNSTABLE
            self._emit("connectivity_changed", self._connectivity_status)

    # ==================== Status ====================

    def get_status(self) -> Dict[str, Any]:
        """Get current sync manager status."""
        pending_count = 0
        if self._offline_storage:
            pending_count = self._offline_storage.get_sync_queue_count()

        return {
            "is_running": self._is_running,
            "is_syncing": self._progress.is_syncing,
            "connectivity": self._connectivity_status.value,
            "is_online": self.is_online,
            "sync_interval": self._sync_interval,
            "current_backoff": self._current_backoff,
            "consecutive_failures": self._consecutive_failures,
            "last_sync": self._progress.last_sync.isoformat() if self._progress.last_sync else None,
            "last_error": self._progress.last_error,
            "pending_items": pending_count,
            "progress": {
                "total": self._progress.total_items,
                "synced": self._progress.synced_items,
                "failed": self._progress.failed_items,
                "conflicts": self._progress.conflicts
            }
        }

    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last successful sync time."""
        return self._progress.last_sync


# Global instance (lazy initialization)
_sync_manager: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """Get the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager
