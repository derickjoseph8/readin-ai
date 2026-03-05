"""
Offline Manager for ReadIn AI Desktop App.

Handles offline-first functionality:
- Network connectivity detection and monitoring
- Queue operations when offline
- Sync queued operations when back online
- Conflict resolution for sync
"""

import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import hashlib

logger = logging.getLogger(__name__)


class NetworkStatus(Enum):
    """Network connectivity status."""
    ONLINE = "online"
    OFFLINE = "offline"
    CHECKING = "checking"
    UNSTABLE = "unstable"
    LIMITED = "limited"  # Internet works but API unreachable


class OperationType(Enum):
    """Types of operations that can be queued."""
    CREATE_MEETING = "create_meeting"
    END_MEETING = "end_meeting"
    SAVE_CONVERSATION = "save_conversation"
    CREATE_ACTION_ITEM = "create_action_item"
    COMPLETE_ACTION_ITEM = "complete_action_item"
    CREATE_COMMITMENT = "create_commitment"
    COMPLETE_COMMITMENT = "complete_commitment"
    UPDATE_MEETING = "update_meeting"
    GENERATE_SUMMARY = "generate_summary"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    NEWEST_WINS = "newest_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class QueuedOperation:
    """Represents an operation queued for later sync."""
    id: str
    operation_type: OperationType
    entity_type: str
    local_id: str
    remote_id: Optional[int]
    data: Dict[str, Any]
    priority: int
    created_at: datetime
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None
    checksum: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    operation_id: str
    entity_type: str
    local_id: str
    remote_id: Optional[int] = None
    error: Optional[str] = None
    conflict: bool = False
    conflict_data: Optional[Dict[str, Any]] = None


@dataclass
class SyncProgress:
    """Current sync progress."""
    total: int = 0
    completed: int = 0
    failed: int = 0
    conflicts: int = 0
    is_syncing: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None

    @property
    def percent(self) -> int:
        if self.total == 0:
            return 100
        return int((self.completed / self.total) * 100)


class OfflineManager:
    """
    Manages offline functionality for ReadIn AI.

    Features:
    - Network connectivity monitoring
    - Operation queuing when offline
    - Background sync when online
    - Conflict detection and resolution
    - Event callbacks for UI updates
    """

    # Connectivity check settings
    CONNECTIVITY_HOSTS = [
        ("8.8.8.8", 53, 3.0),      # Google DNS
        ("1.1.1.1", 53, 3.0),      # Cloudflare DNS
        ("208.67.222.222", 53, 3.0),  # OpenDNS
    ]
    CONNECTIVITY_CHECK_INTERVAL = 30  # seconds
    API_CHECK_TIMEOUT = 5.0

    # Sync settings
    SYNC_INTERVAL = 60  # seconds
    MIN_SYNC_INTERVAL = 30
    MAX_SYNC_INTERVAL = 300
    MAX_RETRY_ATTEMPTS = 5
    RETRY_BACKOFF_BASE = 30  # seconds
    MAX_RETRY_BACKOFF = 480  # 8 minutes

    # Priority levels (higher = more important)
    PRIORITY_CRITICAL = 10
    PRIORITY_HIGH = 8
    PRIORITY_NORMAL = 5
    PRIORITY_LOW = 2

    def __init__(
        self,
        api_client=None,
        local_storage=None,
        conflict_strategy: ConflictResolution = ConflictResolution.SERVER_WINS
    ):
        """
        Initialize offline manager.

        Args:
            api_client: API client for remote operations
            local_storage: LocalStorage instance for persistence
            conflict_strategy: Default conflict resolution strategy
        """
        self._api_client = api_client
        self._local_storage = local_storage
        self._conflict_strategy = conflict_strategy

        # State
        self._network_status = NetworkStatus.CHECKING
        self._is_running = False
        self._sync_progress = SyncProgress()

        # Threads
        self._connectivity_thread: Optional[threading.Thread] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Thread safety
        self._lock = threading.RLock()

        # Event listeners
        self._listeners: Dict[str, List[Callable]] = {
            "status_changed": [],
            "sync_started": [],
            "sync_progress": [],
            "sync_completed": [],
            "sync_error": [],
            "conflict_detected": [],
            "operation_queued": [],
            "operation_synced": [],
        }

        # Last successful connectivity check
        self._last_online_time: Optional[datetime] = None
        self._consecutive_failures = 0

        logger.info("Offline manager initialized")

    # ==================== Properties ====================

    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._network_status == NetworkStatus.ONLINE

    @property
    def is_offline(self) -> bool:
        """Check if currently offline."""
        return self._network_status in (NetworkStatus.OFFLINE, NetworkStatus.LIMITED)

    @property
    def network_status(self) -> NetworkStatus:
        """Get current network status."""
        return self._network_status

    @property
    def sync_progress(self) -> SyncProgress:
        """Get current sync progress."""
        return self._sync_progress

    @property
    def is_syncing(self) -> bool:
        """Check if sync is in progress."""
        return self._sync_progress.is_syncing

    @property
    def pending_operations_count(self) -> int:
        """Get count of pending operations."""
        if self._local_storage:
            return self._local_storage.get_sync_queue_count()
        return 0

    # ==================== Configuration ====================

    def set_api_client(self, api_client):
        """Set or update the API client."""
        self._api_client = api_client

    def set_local_storage(self, local_storage):
        """Set or update the local storage."""
        self._local_storage = local_storage

    def set_conflict_strategy(self, strategy: ConflictResolution):
        """Set default conflict resolution strategy."""
        self._conflict_strategy = strategy

    # ==================== Event System ====================

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
                logger.error(f"Error in listener for {event}: {e}")

    # ==================== Lifecycle ====================

    def start(self) -> bool:
        """Start offline manager services."""
        if self._is_running:
            return True

        self._stop_event.clear()
        self._is_running = True

        # Start connectivity monitoring thread
        self._connectivity_thread = threading.Thread(
            target=self._connectivity_loop,
            daemon=True,
            name="OfflineManager-Connectivity"
        )
        self._connectivity_thread.start()

        # Start sync thread
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="OfflineManager-Sync"
        )
        self._sync_thread.start()

        logger.info("Offline manager started")
        return True

    def stop(self):
        """Stop offline manager services."""
        self._is_running = False
        self._stop_event.set()

        # Wait for threads to finish
        if self._connectivity_thread and self._connectivity_thread.is_alive():
            self._connectivity_thread.join(timeout=5.0)

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)

        self._connectivity_thread = None
        self._sync_thread = None

        logger.info("Offline manager stopped")

    # ==================== Connectivity ====================

    def check_connectivity(self) -> NetworkStatus:
        """
        Check network connectivity.

        Performs:
        1. Basic internet connectivity check (DNS resolution)
        2. API server reachability check

        Returns:
            Current NetworkStatus
        """
        old_status = self._network_status
        self._network_status = NetworkStatus.CHECKING

        # Step 1: Check basic internet connectivity
        internet_available = self._check_internet()

        if not internet_available:
            self._network_status = NetworkStatus.OFFLINE
            self._consecutive_failures += 1
        else:
            # Step 2: Check API server
            api_available = self._check_api_server()

            if api_available:
                self._network_status = NetworkStatus.ONLINE
                self._last_online_time = datetime.now()
                self._consecutive_failures = 0
            else:
                # Internet works but API doesn't
                self._network_status = NetworkStatus.LIMITED
                self._consecutive_failures += 1

        # Detect unstable connection
        if self._consecutive_failures >= 3:
            if self._network_status != NetworkStatus.OFFLINE:
                self._network_status = NetworkStatus.UNSTABLE

        # Emit event if status changed
        if old_status != self._network_status:
            logger.info(f"Network status changed: {old_status.value} -> {self._network_status.value}")
            self._emit("status_changed", self._network_status)

            # Trigger sync if just came online
            if self._network_status == NetworkStatus.ONLINE and old_status != NetworkStatus.ONLINE:
                self._trigger_immediate_sync()

        return self._network_status

    def _check_internet(self) -> bool:
        """Check basic internet connectivity."""
        for host, port, timeout in self.CONNECTIVITY_HOSTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.close()
                return True
            except (socket.timeout, socket.error, OSError):
                continue
        return False

    def _check_api_server(self) -> bool:
        """Check API server reachability."""
        if not self._api_client:
            return False

        try:
            # Use a quick health check endpoint
            result = self._api_client._request_internal(
                "GET", "/health",
                timeout_type="quick"
            )
            return "error" not in result
        except Exception as e:
            logger.debug(f"API check failed: {e}")
            return False

    def _connectivity_loop(self):
        """Background connectivity monitoring loop."""
        while self._is_running:
            try:
                self.check_connectivity()
            except Exception as e:
                logger.error(f"Connectivity check error: {e}")

            # Wait for next check or stop signal
            self._stop_event.wait(timeout=self.CONNECTIVITY_CHECK_INTERVAL)

    # ==================== Operation Queuing ====================

    def queue_operation(
        self,
        operation_type: OperationType,
        entity_type: str,
        local_id: str,
        data: Dict[str, Any],
        remote_id: Optional[int] = None,
        priority: Optional[int] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Queue an operation for later sync.

        Args:
            operation_type: Type of operation
            entity_type: Entity type (meeting, conversation, etc.)
            local_id: Local entity ID
            data: Operation data
            remote_id: Remote entity ID if known
            priority: Operation priority (higher = more important)
            dependencies: List of operation IDs this depends on

        Returns:
            Operation ID
        """
        import uuid

        operation_id = str(uuid.uuid4())

        # Determine priority if not specified
        if priority is None:
            priority = self._get_default_priority(operation_type)

        # Compute checksum for conflict detection
        checksum = self._compute_checksum(data)

        operation = QueuedOperation(
            id=operation_id,
            operation_type=operation_type,
            entity_type=entity_type,
            local_id=local_id,
            remote_id=remote_id,
            data=data,
            priority=priority,
            created_at=datetime.now(),
            checksum=checksum,
            dependencies=dependencies or []
        )

        # Save to local storage
        if self._local_storage:
            self._local_storage.add_sync_operation(
                entity_type=entity_type,
                operation=self._operation_type_to_sync_operation(operation_type),
                entity_id=local_id,
                data={
                    **data,
                    "operation_type": operation_type.value,
                    "checksum": checksum
                },
                priority=priority,
                remote_id=remote_id
            )

        self._emit("operation_queued", operation)
        logger.debug(f"Operation queued: {operation_type.value} for {entity_type}/{local_id}")

        return operation_id

    def _get_default_priority(self, operation_type: OperationType) -> int:
        """Get default priority for operation type."""
        priorities = {
            OperationType.CREATE_MEETING: self.PRIORITY_CRITICAL,
            OperationType.END_MEETING: self.PRIORITY_HIGH,
            OperationType.SAVE_CONVERSATION: self.PRIORITY_NORMAL,
            OperationType.CREATE_ACTION_ITEM: self.PRIORITY_HIGH,
            OperationType.COMPLETE_ACTION_ITEM: self.PRIORITY_NORMAL,
            OperationType.CREATE_COMMITMENT: self.PRIORITY_HIGH,
            OperationType.COMPLETE_COMMITMENT: self.PRIORITY_NORMAL,
            OperationType.UPDATE_MEETING: self.PRIORITY_NORMAL,
            OperationType.GENERATE_SUMMARY: self.PRIORITY_LOW,
        }
        return priorities.get(operation_type, self.PRIORITY_NORMAL)

    def _operation_type_to_sync_operation(self, op_type: OperationType):
        """Convert OperationType to SyncOperation."""
        from .local_storage import SyncOperation

        if op_type in (
            OperationType.CREATE_MEETING,
            OperationType.SAVE_CONVERSATION,
            OperationType.CREATE_ACTION_ITEM,
            OperationType.CREATE_COMMITMENT
        ):
            return SyncOperation.CREATE

        if op_type in (
            OperationType.END_MEETING,
            OperationType.COMPLETE_ACTION_ITEM,
            OperationType.COMPLETE_COMMITMENT,
            OperationType.UPDATE_MEETING,
            OperationType.GENERATE_SUMMARY
        ):
            return SyncOperation.UPDATE

        return SyncOperation.UPDATE

    # ==================== Sync Operations ====================

    def sync_now(self) -> bool:
        """Trigger immediate sync."""
        if not self.is_online:
            logger.warning("Cannot sync: offline")
            return False

        if self.is_syncing:
            logger.debug("Sync already in progress")
            return False

        self._trigger_immediate_sync()
        return True

    def _trigger_immediate_sync(self):
        """Trigger sync in background."""
        threading.Thread(
            target=self._perform_sync,
            daemon=True,
            name="ImmediateSync"
        ).start()

    def _sync_loop(self):
        """Background sync loop."""
        while self._is_running:
            try:
                if self.is_online and not self.is_syncing:
                    if self.pending_operations_count > 0:
                        self._perform_sync()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")

            # Wait for next sync interval or stop signal
            self._stop_event.wait(timeout=self.SYNC_INTERVAL)

    def _perform_sync(self):
        """Perform synchronization of queued operations."""
        if not self._api_client or not self._local_storage:
            logger.warning("Cannot sync: missing API client or storage")
            return

        with self._lock:
            if self._sync_progress.is_syncing:
                return
            self._sync_progress.is_syncing = True
            self._sync_progress.started_at = datetime.now()
            self._sync_progress.completed = 0
            self._sync_progress.failed = 0
            self._sync_progress.conflicts = 0

        self._emit("sync_started")
        logger.info("Starting sync...")

        try:
            # Get pending operations
            pending = self._local_storage.get_pending_syncs()
            self._sync_progress.total = len(pending)

            if not pending:
                logger.debug("No pending operations to sync")
                self._complete_sync()
                return

            logger.info(f"Syncing {len(pending)} pending operations")

            for op in pending:
                if not self._is_running or not self.is_online:
                    break

                result = self._sync_operation(op)

                if result.success:
                    self._sync_progress.completed += 1
                    self._local_storage.mark_sync_success(op.id, result.remote_id)
                    self._emit("operation_synced", op, result)
                elif result.conflict:
                    self._sync_progress.conflicts += 1
                    self._handle_conflict(op, result)
                else:
                    self._sync_progress.failed += 1
                    self._local_storage.mark_sync_failure(op.id, result.error or "Unknown error")

                self._emit("sync_progress", self._sync_progress)

            self._complete_sync()

        except Exception as e:
            logger.error(f"Sync error: {e}")
            self._sync_progress.last_error = str(e)
            self._emit("sync_error", str(e))
            self._complete_sync()

    def _sync_operation(self, op) -> SyncResult:
        """
        Sync a single queued operation.

        Args:
            op: PendingSyncOperation to sync

        Returns:
            SyncResult
        """
        try:
            entity_type = op.entity_type
            operation = op.operation
            data = op.data

            operation_type = data.get("operation_type")

            # Route to appropriate handler
            if operation_type == OperationType.CREATE_MEETING.value:
                return self._sync_create_meeting(op)
            elif operation_type == OperationType.END_MEETING.value:
                return self._sync_end_meeting(op)
            elif operation_type == OperationType.SAVE_CONVERSATION.value:
                return self._sync_save_conversation(op)
            elif operation_type == OperationType.CREATE_ACTION_ITEM.value:
                return self._sync_create_action_item(op)
            elif operation_type == OperationType.COMPLETE_ACTION_ITEM.value:
                return self._sync_complete_action_item(op)
            elif operation_type == OperationType.CREATE_COMMITMENT.value:
                return self._sync_create_commitment(op)
            elif operation_type == OperationType.COMPLETE_COMMITMENT.value:
                return self._sync_complete_commitment(op)
            else:
                # Fallback to entity-type based sync
                return self._sync_by_entity_type(op)

        except Exception as e:
            logger.error(f"Error syncing operation {op.id}: {e}")
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type=op.entity_type,
                local_id=op.entity_id,
                error=str(e)
            )

    def _sync_create_meeting(self, op) -> SyncResult:
        """Sync create meeting operation."""
        data = op.data

        result = self._api_client.start_meeting(
            meeting_type=data.get("meeting_type", "general"),
            title=data.get("title"),
            meeting_app=data.get("meeting_app")
        )

        if "error" in result:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="meeting",
                local_id=op.entity_id,
                error=result.get("message", "Failed to create meeting")
            )

        # Update local storage with remote ID
        remote_id = result.get("id")
        if remote_id and self._local_storage:
            self._local_storage.set_id_mapping("meeting", op.entity_id, remote_id)

        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="meeting",
            local_id=op.entity_id,
            remote_id=remote_id
        )

    def _sync_end_meeting(self, op) -> SyncResult:
        """Sync end meeting operation."""
        remote_id = op.remote_id

        # Try to get remote_id from mapping if not set
        if not remote_id and self._local_storage:
            remote_id = self._local_storage.get_remote_id("meeting", op.entity_id)

        if not remote_id:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="meeting",
                local_id=op.entity_id,
                error="Meeting not yet synced to server"
            )

        result = self._api_client.end_meeting(remote_id)

        if "error" in result:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="meeting",
                local_id=op.entity_id,
                error=result.get("message", "Failed to end meeting")
            )

        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="meeting",
            local_id=op.entity_id,
            remote_id=remote_id
        )

    def _sync_save_conversation(self, op) -> SyncResult:
        """Sync save conversation operation."""
        data = op.data

        # Get meeting remote_id
        meeting_id = data.get("meeting_id")
        if not meeting_id:
            meeting_local_id = data.get("meeting_local_id")
            if meeting_local_id and self._local_storage:
                meeting_id = self._local_storage.get_remote_id("meeting", meeting_local_id)

        if not meeting_id:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="conversation",
                local_id=op.entity_id,
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
                operation_id=op.id,
                entity_type="conversation",
                local_id=op.entity_id,
                error=result.get("message", "Failed to save conversation")
            )

        remote_id = result.get("id")
        if remote_id and self._local_storage:
            self._local_storage.set_id_mapping("conversation", op.entity_id, remote_id)

        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="conversation",
            local_id=op.entity_id,
            remote_id=remote_id
        )

    def _sync_create_action_item(self, op) -> SyncResult:
        """Sync create action item operation."""
        # API would need endpoint for direct action item creation
        # For now, action items are typically created through meeting summary
        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="action_item",
            local_id=op.entity_id
        )

    def _sync_complete_action_item(self, op) -> SyncResult:
        """Sync complete action item operation."""
        remote_id = op.remote_id

        if not remote_id and self._local_storage:
            remote_id = self._local_storage.get_remote_id("action_item", op.entity_id)

        if not remote_id:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="action_item",
                local_id=op.entity_id,
                error="Action item not yet synced"
            )

        result = self._api_client.complete_action_item(remote_id)

        if "error" in result:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="action_item",
                local_id=op.entity_id,
                error=result.get("message", "Failed to complete action item")
            )

        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="action_item",
            local_id=op.entity_id,
            remote_id=remote_id
        )

    def _sync_create_commitment(self, op) -> SyncResult:
        """Sync create commitment operation."""
        # Commitments are typically extracted from meeting summaries
        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="commitment",
            local_id=op.entity_id
        )

    def _sync_complete_commitment(self, op) -> SyncResult:
        """Sync complete commitment operation."""
        remote_id = op.remote_id

        if not remote_id and self._local_storage:
            remote_id = self._local_storage.get_remote_id("commitment", op.entity_id)

        if not remote_id:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="commitment",
                local_id=op.entity_id,
                error="Commitment not yet synced"
            )

        result = self._api_client.complete_commitment(remote_id)

        if "error" in result:
            return SyncResult(
                success=False,
                operation_id=op.id,
                entity_type="commitment",
                local_id=op.entity_id,
                error=result.get("message", "Failed to complete commitment")
            )

        return SyncResult(
            success=True,
            operation_id=op.id,
            entity_type="commitment",
            local_id=op.entity_id,
            remote_id=remote_id
        )

    def _sync_by_entity_type(self, op) -> SyncResult:
        """Fallback sync based on entity type."""
        entity_type = op.entity_type
        operation = op.operation
        data = op.data

        if entity_type == "meeting":
            if operation == "create":
                return self._sync_create_meeting(op)
            elif operation == "update":
                return self._sync_end_meeting(op)

        elif entity_type == "conversation":
            if operation == "create":
                return self._sync_save_conversation(op)

        elif entity_type == "action_item":
            if operation == "update" and data.get("completed"):
                return self._sync_complete_action_item(op)

        elif entity_type == "commitment":
            if operation == "update" and data.get("completed"):
                return self._sync_complete_commitment(op)

        return SyncResult(
            success=False,
            operation_id=op.id,
            entity_type=entity_type,
            local_id=op.entity_id,
            error=f"Unknown operation: {operation} for {entity_type}"
        )

    def _complete_sync(self):
        """Complete sync process."""
        with self._lock:
            self._sync_progress.is_syncing = False
            self._sync_progress.completed_at = datetime.now()

        logger.info(
            f"Sync completed: {self._sync_progress.completed} synced, "
            f"{self._sync_progress.failed} failed, "
            f"{self._sync_progress.conflicts} conflicts"
        )

        self._emit("sync_completed", self._sync_progress)

    # ==================== Conflict Resolution ====================

    def _handle_conflict(self, op, result: SyncResult):
        """Handle a sync conflict."""
        logger.warning(f"Conflict detected for {op.entity_type}/{op.entity_id}")
        self._emit("conflict_detected", op, result)

        # Record conflict for later resolution
        if self._local_storage and result.conflict_data:
            conflict_id = self._local_storage.record_conflict(
                entity_type=op.entity_type,
                entity_id=op.entity_id,
                local_data=op.data,
                server_data=result.conflict_data
            )

            logger.info(f"Conflict recorded: {conflict_id}")

        # Apply resolution strategy
        if self._conflict_strategy == ConflictResolution.SERVER_WINS:
            # Server data takes precedence - mark as synced
            if self._local_storage:
                self._local_storage.mark_sync_success(op.id, op.remote_id)

        elif self._conflict_strategy == ConflictResolution.CLIENT_WINS:
            # Client data takes precedence - retry with force
            # Would need API support for force update
            pass

        elif self._conflict_strategy == ConflictResolution.NEWEST_WINS:
            # Compare timestamps and use newer data
            self._resolve_by_timestamp(op, result)

        elif self._conflict_strategy == ConflictResolution.MERGE:
            # Attempt to merge changes
            self._attempt_merge(op, result)

        elif self._conflict_strategy == ConflictResolution.MANUAL:
            # Leave for user resolution
            pass

    def _resolve_by_timestamp(self, op, result: SyncResult):
        """Resolve conflict by timestamp (newest wins)."""
        local_time = op.created_at
        server_time = None

        if result.conflict_data and "updated_at" in result.conflict_data:
            try:
                server_time = datetime.fromisoformat(result.conflict_data["updated_at"])
            except (ValueError, TypeError):
                pass

        if server_time and server_time > local_time:
            # Server is newer - accept server data
            if self._local_storage:
                self._local_storage.mark_sync_success(op.id, op.remote_id)
        else:
            # Local is newer - mark for retry
            pass

    def _attempt_merge(self, op, result: SyncResult):
        """Attempt to merge local and server changes."""
        if not result.conflict_data:
            return

        # Simple field-by-field merge
        local_data = op.data
        server_data = result.conflict_data

        merged = {}
        all_keys = set(local_data.keys()) | set(server_data.keys())

        for key in all_keys:
            local_val = local_data.get(key)
            server_val = server_data.get(key)

            if local_val == server_val:
                merged[key] = local_val
            elif local_val is None:
                merged[key] = server_val
            elif server_val is None:
                merged[key] = local_val
            else:
                # Both have different values - prefer server for now
                merged[key] = server_val

        # Store merged result
        # Would need to update local storage and retry sync
        logger.info(f"Merged conflict for {op.entity_type}/{op.entity_id}")

    def resolve_conflict_manually(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        resolved_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Manually resolve a conflict.

        Args:
            conflict_id: Conflict ID
            resolution: Resolution strategy to apply
            resolved_data: Optional data to use for resolution

        Returns:
            True if conflict was resolved
        """
        if not self._local_storage:
            return False

        return self._local_storage.resolve_conflict(conflict_id, resolution, resolved_data)

    def get_unresolved_conflicts(self) -> List[Dict[str, Any]]:
        """Get list of unresolved conflicts."""
        if not self._local_storage:
            return []

        conflicts = self._local_storage.get_unresolved_conflicts()
        return [
            {
                "id": c.id,
                "entity_type": c.entity_type,
                "entity_id": c.entity_id,
                "local_data": c.local_data,
                "server_data": c.server_data,
                "created_at": c.created_at.isoformat()
            }
            for c in conflicts
        ]

    # ==================== Utility Methods ====================

    def _compute_checksum(self, data: Dict[str, Any]) -> str:
        """Compute checksum for conflict detection."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()

    def get_status(self) -> Dict[str, Any]:
        """Get offline manager status."""
        return {
            "is_running": self._is_running,
            "network_status": self._network_status.value,
            "is_online": self.is_online,
            "is_syncing": self.is_syncing,
            "pending_operations": self.pending_operations_count,
            "last_online": self._last_online_time.isoformat() if self._last_online_time else None,
            "consecutive_failures": self._consecutive_failures,
            "sync_progress": {
                "total": self._sync_progress.total,
                "completed": self._sync_progress.completed,
                "failed": self._sync_progress.failed,
                "conflicts": self._sync_progress.conflicts,
                "percent": self._sync_progress.percent
            },
            "last_sync": self._sync_progress.completed_at.isoformat() if self._sync_progress.completed_at else None,
            "last_error": self._sync_progress.last_error
        }


# Global instance
_offline_manager: Optional[OfflineManager] = None


def get_offline_manager() -> OfflineManager:
    """Get global offline manager instance."""
    global _offline_manager
    if _offline_manager is None:
        _offline_manager = OfflineManager()
    return _offline_manager
