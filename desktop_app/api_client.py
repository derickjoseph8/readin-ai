"""
Enhanced API Client for ReadIn AI Desktop App.

Extends the base API client with:
- Connectivity checks before requests
- Automatic queuing of failed requests for later sync
- Local cache fallback when offline
- Seamless online/offline operation
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

# Import base API client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api_client import (
    APIClient,
    APIClientError,
    ConnectionError as APIConnectionError,
    TimeoutError as APITimeoutError,
)

from .local_storage import LocalStorage, CachePolicy, get_local_storage
from .offline_manager import (
    OfflineManager,
    NetworkStatus,
    OperationType,
    get_offline_manager,
)

logger = logging.getLogger(__name__)


class EnhancedAPIClient(APIClient):
    """
    Enhanced API client with offline-first functionality.

    Extends the base APIClient to provide:
    - Automatic connectivity detection
    - Request queuing when offline
    - Local cache for offline access
    - Seamless sync when back online
    """

    def __init__(
        self,
        offline_manager: Optional[OfflineManager] = None,
        local_storage: Optional[LocalStorage] = None,
        auto_start: bool = True
    ):
        """
        Initialize enhanced API client.

        Args:
            offline_manager: OfflineManager instance
            local_storage: LocalStorage instance
            auto_start: Whether to auto-start offline manager
        """
        super().__init__()

        self._offline_manager = offline_manager or get_offline_manager()
        self._local_storage = local_storage or get_local_storage()

        # Configure offline manager with this client
        self._offline_manager.set_api_client(self)
        self._offline_manager.set_local_storage(self._local_storage)

        # Event handlers
        self._offline_manager.add_listener("status_changed", self._on_status_changed)
        self._offline_manager.add_listener("sync_completed", self._on_sync_completed)

        # Cache settings
        self._cache_enabled = True
        self._cache_policy = CachePolicy.MEDIUM

        # Start offline manager
        if auto_start:
            self._offline_manager.start()

        logger.info("Enhanced API client initialized with offline support")

    # ==================== Properties ====================

    @property
    def is_offline(self) -> bool:
        """Check if currently offline."""
        return self._offline_manager.is_offline

    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._offline_manager.is_online

    @property
    def network_status(self) -> NetworkStatus:
        """Get current network status."""
        return self._offline_manager.network_status

    @property
    def pending_sync_count(self) -> int:
        """Get number of pending sync operations."""
        return self._offline_manager.pending_operations_count

    @property
    def offline_manager(self) -> OfflineManager:
        """Get offline manager instance."""
        return self._offline_manager

    @property
    def local_storage(self) -> LocalStorage:
        """Get local storage instance."""
        return self._local_storage

    # ==================== Configuration ====================

    def set_cache_enabled(self, enabled: bool):
        """Enable or disable caching."""
        self._cache_enabled = enabled

    def set_cache_policy(self, policy: CachePolicy):
        """Set default cache policy."""
        self._cache_policy = policy

    # ==================== Event Handlers ====================

    def _on_status_changed(self, status: NetworkStatus):
        """Handle network status change."""
        logger.info(f"Network status changed: {status.value}")

        # Notify connectivity listeners from parent class
        for listener in self._connectivity_listeners:
            try:
                listener(status == NetworkStatus.ONLINE)
            except Exception as e:
                logger.error(f"Error in connectivity listener: {e}")

    def _on_sync_completed(self, progress):
        """Handle sync completion."""
        logger.info(
            f"Sync completed: {progress.completed} synced, "
            f"{progress.failed} failed, {progress.conflicts} conflicts"
        )

    # ==================== Connectivity ====================

    def check_connectivity(self) -> bool:
        """Check current connectivity."""
        status = self._offline_manager.check_connectivity()
        return status == NetworkStatus.ONLINE

    def force_offline(self):
        """Force offline mode (for testing or user preference)."""
        self._offline_manager._network_status = NetworkStatus.OFFLINE
        self._offline_manager._emit("status_changed", NetworkStatus.OFFLINE)

    def force_online_check(self):
        """Force an immediate connectivity check."""
        self._offline_manager.check_connectivity()

    # ==================== Sync ====================

    def sync_now(self) -> bool:
        """Trigger immediate sync."""
        return self._offline_manager.sync_now()

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return self._offline_manager.get_status()

    # ==================== Enhanced API Methods ====================

    def start_meeting(
        self,
        meeting_type: str = "general",
        title: Optional[str] = None,
        meeting_app: Optional[str] = None
    ) -> Dict:
        """
        Start a new meeting session with offline support.

        When offline, creates meeting locally and queues for sync.
        """
        # Try online first
        if self.is_online:
            result = super().start_meeting(meeting_type, title, meeting_app)

            if "error" not in result:
                # Cache the meeting
                remote_id = result.get("id")
                local_id = self._local_storage.save_meeting(
                    meeting_type=meeting_type,
                    title=title,
                    meeting_app=meeting_app,
                    remote_id=remote_id
                )
                result["local_id"] = local_id
                return result

        # Offline: create locally and queue
        local_id = self._local_storage.save_meeting(
            meeting_type=meeting_type,
            title=title,
            meeting_app=meeting_app
        )

        self._offline_manager.queue_operation(
            operation_type=OperationType.CREATE_MEETING,
            entity_type="meeting",
            local_id=local_id,
            data={
                "meeting_type": meeting_type,
                "title": title,
                "meeting_app": meeting_app
            }
        )

        logger.info(f"Meeting created offline: {local_id}")
        return {
            "local_id": local_id,
            "id": None,
            "meeting_type": meeting_type,
            "title": title,
            "meeting_app": meeting_app,
            "status": "active",
            "offline": True,
            "message": "Meeting saved offline"
        }

    def end_meeting(self, meeting_id: int) -> Dict:
        """
        End a meeting session with offline support.

        Args:
            meeting_id: Remote meeting ID (or local_id if offline)
        """
        # Get local_id if we have remote_id
        local_id = self._local_storage.get_local_id("meeting", meeting_id)

        # Try online first
        if self.is_online and meeting_id:
            result = super().end_meeting(meeting_id)

            if "error" not in result:
                # Update local cache
                if local_id:
                    self._local_storage.end_meeting(local_id)
                return result

        # Offline: update locally and queue
        if local_id:
            self._local_storage.end_meeting(local_id)

            self._offline_manager.queue_operation(
                operation_type=OperationType.END_MEETING,
                entity_type="meeting",
                local_id=local_id,
                remote_id=meeting_id,
                data={"ended_at": datetime.now().isoformat()}
            )

            return {
                "success": True,
                "local_id": local_id,
                "offline": True,
                "message": "Meeting ended offline"
            }

        return {"error": True, "message": "Meeting not found"}

    def end_meeting_by_local_id(self, local_id: str) -> Dict:
        """
        End a meeting using local ID.

        Useful when working offline and don't have remote ID.
        """
        meeting = self._local_storage.get_meeting(local_id)
        if not meeting:
            return {"error": True, "message": "Meeting not found"}

        remote_id = meeting.get("remote_id")

        # Try online first if we have remote_id
        if self.is_online and remote_id:
            result = super().end_meeting(remote_id)
            if "error" not in result:
                self._local_storage.end_meeting(local_id)
                return result

        # Offline: update locally and queue
        self._local_storage.end_meeting(local_id)

        self._offline_manager.queue_operation(
            operation_type=OperationType.END_MEETING,
            entity_type="meeting",
            local_id=local_id,
            remote_id=remote_id,
            data={"ended_at": datetime.now().isoformat()}
        )

        return {
            "success": True,
            "local_id": local_id,
            "offline": True
        }

    def get_active_meeting(self) -> Optional[Dict]:
        """
        Get active meeting with offline support.

        Falls back to local cache when offline.
        """
        # Try online first
        if self.is_online:
            result = super().get_active_meeting()
            if result and "error" not in result:
                return result

        # Offline: get from local storage
        meeting = self._local_storage.get_active_meeting()
        if meeting:
            meeting["offline"] = True
        return meeting

    def get_meeting(self, meeting_id: int) -> Dict:
        """
        Get meeting details with offline support.

        Falls back to local cache when offline.
        """
        # Check local cache first
        cache_key = f"meeting:{meeting_id}"
        cached = self._local_storage.cache_get(cache_key)

        if self.is_online:
            result = super().get_meeting(meeting_id)

            if "error" not in result:
                # Update cache
                self._local_storage.cache_set(
                    cache_key, result, "meeting", self._cache_policy
                )
                return result

        # Return cached or local data
        if cached:
            cached["offline"] = True
            return cached

        # Try local storage by remote_id
        local_id = self._local_storage.get_local_id("meeting", meeting_id)
        if local_id:
            meeting = self._local_storage.get_meeting(local_id)
            if meeting:
                meeting["offline"] = True
                return meeting

        return {"error": True, "message": "Meeting not found", "offline": True}

    def list_meetings(
        self,
        limit: int = 20,
        meeting_type: Optional[str] = None
    ) -> List[Dict]:
        """
        List meetings with offline support.

        Combines local and remote meetings when online,
        returns local only when offline.
        """
        # Get local meetings
        local_meetings = self._local_storage.get_meetings(
            limit=limit,
            meeting_type=meeting_type
        )

        if self.is_online:
            remote_meetings = super().list_meetings(limit, meeting_type)

            if remote_meetings:
                # Merge local and remote, removing duplicates by remote_id
                remote_ids = {m.get("id") for m in remote_meetings if m.get("id")}
                local_only = [
                    m for m in local_meetings
                    if not m.get("remote_id") or m.get("remote_id") not in remote_ids
                ]

                # Add offline flag to local-only meetings
                for m in local_only:
                    m["offline"] = True

                return remote_meetings + local_only

        # Offline: return local only
        for m in local_meetings:
            m["offline"] = True
        return local_meetings

    def save_conversation(
        self,
        meeting_id: int,
        heard_text: str,
        response_text: str,
        speaker: Optional[str] = None
    ) -> Dict:
        """
        Save conversation with offline support.
        """
        # Get local meeting ID
        local_meeting_id = self._local_storage.get_local_id("meeting", meeting_id)

        # Try online first
        if self.is_online and meeting_id:
            result = super().save_conversation(
                meeting_id, heard_text, response_text, speaker
            )

            if "error" not in result:
                # Cache locally
                if local_meeting_id:
                    self._local_storage.save_conversation(
                        meeting_local_id=local_meeting_id,
                        heard_text=heard_text,
                        response_text=response_text,
                        speaker=speaker,
                        remote_id=result.get("id")
                    )
                return result

        # Offline: save locally and queue
        if local_meeting_id:
            local_id = self._local_storage.save_conversation(
                meeting_local_id=local_meeting_id,
                heard_text=heard_text,
                response_text=response_text,
                speaker=speaker
            )

            self._offline_manager.queue_operation(
                operation_type=OperationType.SAVE_CONVERSATION,
                entity_type="conversation",
                local_id=local_id,
                data={
                    "meeting_local_id": local_meeting_id,
                    "meeting_id": meeting_id,
                    "heard_text": heard_text,
                    "response_text": response_text,
                    "speaker": speaker
                }
            )

            return {
                "local_id": local_id,
                "id": None,
                "offline": True,
                "message": "Conversation saved offline"
            }

        return {"error": True, "message": "Meeting not found"}

    def save_conversation_offline(
        self,
        meeting_local_id: str,
        heard_text: str,
        response_text: str,
        speaker: Optional[str] = None
    ) -> Dict:
        """
        Save conversation using local meeting ID.

        Useful when working offline without remote IDs.
        """
        meeting = self._local_storage.get_meeting(meeting_local_id)
        if not meeting:
            return {"error": True, "message": "Meeting not found"}

        remote_id = meeting.get("remote_id")

        # Save locally
        local_id = self._local_storage.save_conversation(
            meeting_local_id=meeting_local_id,
            heard_text=heard_text,
            response_text=response_text,
            speaker=speaker
        )

        # Try online sync if possible
        if self.is_online and remote_id:
            result = super().save_conversation(
                remote_id, heard_text, response_text, speaker
            )
            if "error" not in result:
                self._local_storage.set_id_mapping(
                    "conversation", local_id, result.get("id")
                )
                return {**result, "local_id": local_id}

        # Queue for later sync
        self._offline_manager.queue_operation(
            operation_type=OperationType.SAVE_CONVERSATION,
            entity_type="conversation",
            local_id=local_id,
            data={
                "meeting_local_id": meeting_local_id,
                "meeting_id": remote_id,
                "heard_text": heard_text,
                "response_text": response_text,
                "speaker": speaker
            }
        )

        return {
            "local_id": local_id,
            "id": None,
            "offline": True
        }

    def get_task_dashboard(self) -> Dict:
        """
        Get task dashboard with offline support.
        """
        # Try online first
        if self.is_online:
            result = super().get_task_dashboard()

            if "error" not in result:
                # Cache result
                self._local_storage.cache_set(
                    "task_dashboard", result, "dashboard", CachePolicy.SHORT
                )
                return result

        # Offline: get from local storage
        cached = self._local_storage.cache_get("task_dashboard")
        if cached:
            cached["offline"] = True
            return cached

        # Build from local data
        action_items = self._local_storage.get_action_items(include_completed=False)
        commitments = self._local_storage.get_commitments(include_completed=False)

        return {
            "action_items": action_items,
            "commitments": commitments,
            "offline": True
        }

    def complete_action_item(self, action_id: int) -> Dict:
        """
        Complete action item with offline support.
        """
        local_id = self._local_storage.get_local_id("action_item", action_id)

        # Try online first
        if self.is_online and action_id:
            result = super().complete_action_item(action_id)

            if "error" not in result:
                if local_id:
                    self._local_storage.complete_action_item(local_id)
                return result

        # Offline: complete locally and queue
        if local_id:
            self._local_storage.complete_action_item(local_id)

            self._offline_manager.queue_operation(
                operation_type=OperationType.COMPLETE_ACTION_ITEM,
                entity_type="action_item",
                local_id=local_id,
                remote_id=action_id,
                data={"completed": True}
            )

            return {
                "success": True,
                "local_id": local_id,
                "offline": True
            }

        return {"error": True, "message": "Action item not found"}

    def complete_action_item_by_local_id(self, local_id: str) -> Dict:
        """
        Complete action item using local ID.
        """
        action = self._local_storage.get_action_items(include_completed=True)
        target = next((a for a in action if a.get("local_id") == local_id), None)

        if not target:
            return {"error": True, "message": "Action item not found"}

        remote_id = target.get("remote_id")

        # Try online if we have remote_id
        if self.is_online and remote_id:
            result = super().complete_action_item(remote_id)
            if "error" not in result:
                self._local_storage.complete_action_item(local_id)
                return result

        # Complete locally and queue
        self._local_storage.complete_action_item(local_id)

        self._offline_manager.queue_operation(
            operation_type=OperationType.COMPLETE_ACTION_ITEM,
            entity_type="action_item",
            local_id=local_id,
            remote_id=remote_id,
            data={"completed": True}
        )

        return {
            "success": True,
            "local_id": local_id,
            "offline": True
        }

    def complete_commitment(self, commitment_id: int) -> Dict:
        """
        Complete commitment with offline support.
        """
        local_id = self._local_storage.get_local_id("commitment", commitment_id)

        if self.is_online and commitment_id:
            result = super().complete_commitment(commitment_id)

            if "error" not in result:
                # Would need local commitment completion method
                return result

        # Offline handling would go here
        return {"error": True, "message": "Offline commitment completion not supported"}

    # ==================== User/Status Methods ====================

    def get_status(self) -> Dict:
        """
        Get user status with offline support.
        """
        # Try online first
        if self.is_online:
            result = super().get_status()

            if "error" not in result:
                # Cache status
                self._local_storage.cache_set(
                    "user_status", result, "user", CachePolicy.MEDIUM
                )
                return result

        # Offline: return cached status
        cached = self._local_storage.cache_get("user_status")
        if cached:
            cached["offline"] = True
            return cached

        return {
            "error": "offline",
            "message": "Status unavailable offline",
            "offline": True
        }

    def get_user(self) -> Dict:
        """
        Get user profile with offline support.
        """
        if self.is_online:
            result = super().get_user()

            if "error" not in result:
                self._local_storage.cache_set(
                    "user_profile", result, "user", CachePolicy.LONG
                )
                return result

        cached = self._local_storage.cache_get("user_profile")
        if cached:
            cached["offline"] = True
            return cached

        return {
            "error": "offline",
            "message": "User profile unavailable offline",
            "offline": True
        }

    def get_professions(self, category: Optional[str] = None) -> List[Dict]:
        """
        Get professions with offline support (cached).
        """
        cache_key = f"professions:{category or 'all'}"

        if self.is_online:
            result = super().get_professions(category)

            if result:
                self._local_storage.cache_set(
                    cache_key, result, "reference", CachePolicy.LONG
                )
                return result

        cached = self._local_storage.cache_get(cache_key)
        return cached if cached else []

    def get_ai_context(self) -> Dict:
        """
        Get AI context with offline support.
        """
        if self.is_online:
            result = super().get_ai_context()

            if "error" not in result:
                self._local_storage.cache_set(
                    "ai_context", result, "context", CachePolicy.MEDIUM
                )
                return result

        cached = self._local_storage.cache_get("ai_context")
        if cached:
            cached["offline"] = True
            return cached

        return {"offline": True, "message": "AI context unavailable offline"}

    # ==================== Briefings ====================

    def generate_briefing(
        self,
        participant_names: List[str] = None,
        meeting_context: Optional[str] = None,
        meeting_type: Optional[str] = None
    ) -> Dict:
        """
        Generate briefing (online only - AI generation required).
        """
        if not self.is_online:
            return {
                "error": "offline",
                "message": "Briefing generation requires internet connection",
                "offline": True
            }

        return super().generate_briefing(
            participant_names, meeting_context, meeting_type
        )

    # ==================== Utility ====================

    def get_offline_status(self) -> Dict[str, Any]:
        """
        Get comprehensive offline status.
        """
        storage_status = self._local_storage.get_status()
        manager_status = self._offline_manager.get_status()

        return {
            "network": {
                "status": manager_status["network_status"],
                "is_online": manager_status["is_online"],
                "last_online": manager_status.get("last_online"),
            },
            "sync": {
                "is_syncing": manager_status["is_syncing"],
                "pending_operations": manager_status["pending_operations"],
                "progress": manager_status["sync_progress"],
                "last_sync": manager_status.get("last_sync"),
                "last_error": manager_status.get("last_error"),
            },
            "storage": {
                "size_mb": storage_status["storage_size_mb"],
                "max_mb": storage_status["max_storage_mb"],
                "meetings": storage_status["meeting_count"],
                "conversations": storage_status["conversation_count"],
                "pending_syncs": storage_status["pending_syncs"],
                "conflicts": storage_status["unresolved_conflicts"],
            }
        }

    def clear_cache(self, entity_type: Optional[str] = None):
        """Clear local cache."""
        self._local_storage.cache_clear(entity_type)

    def cleanup(self, days: int = 30):
        """Clean up old cached data."""
        self._local_storage.cleanup_old_data(days)

    def close(self):
        """Shutdown the enhanced API client."""
        self._offline_manager.stop()
        self._local_storage.close()
        logger.info("Enhanced API client closed")


# Global instance
_enhanced_api_client: Optional[EnhancedAPIClient] = None


def get_enhanced_api_client() -> EnhancedAPIClient:
    """Get global enhanced API client instance."""
    global _enhanced_api_client
    if _enhanced_api_client is None:
        _enhanced_api_client = EnhancedAPIClient()
    return _enhanced_api_client
