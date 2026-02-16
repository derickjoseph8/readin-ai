"""
Backend synchronization service.

Provides:
- Reliable API communication
- Offline queue and retry
- Background synchronization
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import queue
import time
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class SyncItem:
    """Item to sync with backend."""
    id: str
    endpoint: str
    method: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    attempts: int = 0
    last_error: Optional[str] = None


class SyncService:
    """
    Service for backend synchronization.

    Handles:
    - API communication with retry
    - Offline queue persistence
    - Background sync
    """

    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    SYNC_INTERVAL = 30  # seconds

    def __init__(self, api_client=None, cache_dir: str = None):
        """
        Initialize sync service.

        Args:
            api_client: Backend API client
            cache_dir: Directory for offline queue persistence
        """
        self._api_client = api_client
        self._cache_dir = cache_dir or os.path.expanduser("~/.readin/sync")
        self._sync_queue: queue.Queue = queue.Queue()
        self._pending_items: List[SyncItem] = []
        self._is_running = False
        self._sync_thread: Optional[threading.Thread] = None
        self._is_online = True
        self._listeners: Dict[str, List[Callable]] = {
            "sync_success": [],
            "sync_failure": [],
            "online_status": [],
        }

        # Ensure cache directory exists
        os.makedirs(self._cache_dir, exist_ok=True)

    @property
    def is_running(self) -> bool:
        """Check if sync service is running."""
        return self._is_running

    @property
    def is_online(self) -> bool:
        """Check if backend is reachable."""
        return self._is_online

    @property
    def pending_count(self) -> int:
        """Get number of pending sync items."""
        return len(self._pending_items) + self._sync_queue.qsize()

    def set_api_client(self, api_client):
        """Set or update API client."""
        self._api_client = api_client

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
                logger.error(f"Error in sync listener: {e}")

    def start(self) -> bool:
        """Start sync service."""
        if self._is_running:
            return True

        # Load persisted queue
        self._load_queue()

        self._is_running = True
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True
        )
        self._sync_thread.start()

        logger.info("Sync service started")
        return True

    def stop(self):
        """Stop sync service."""
        self._is_running = False

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)

        # Persist queue before stopping
        self._save_queue()

        self._sync_thread = None
        logger.info("Sync service stopped")

    def queue_sync(
        self,
        endpoint: str,
        method: str = "POST",
        data: Dict[str, Any] = None,
        item_id: str = None
    ):
        """
        Queue an item for synchronization.

        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            item_id: Optional unique ID for deduplication
        """
        import uuid

        item = SyncItem(
            id=item_id or str(uuid.uuid4()),
            endpoint=endpoint,
            method=method,
            data=data or {},
        )

        self._sync_queue.put(item)
        logger.debug(f"Queued sync item: {endpoint}")

    async def sync_now(self, item: SyncItem) -> bool:
        """
        Immediately sync an item.

        Args:
            item: Item to sync

        Returns:
            True if sync successful
        """
        if not self._api_client:
            logger.warning("No API client configured")
            return False

        try:
            if item.method == "POST":
                result = await self._api_client.post(item.endpoint, item.data)
            elif item.method == "PUT":
                result = await self._api_client.put(item.endpoint, item.data)
            elif item.method == "PATCH":
                result = await self._api_client.patch(item.endpoint, item.data)
            elif item.method == "DELETE":
                result = await self._api_client.delete(item.endpoint)
            else:
                logger.error(f"Unknown method: {item.method}")
                return False

            self._is_online = True
            self._emit("sync_success", item)
            return True

        except Exception as e:
            item.attempts += 1
            item.last_error = str(e)
            logger.error(f"Sync failed for {item.endpoint}: {e}")

            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                self._update_online_status(False)

            self._emit("sync_failure", item, e)
            return False

    def _sync_loop(self):
        """Background sync loop."""
        import asyncio

        while self._is_running:
            try:
                # Process queue
                items_to_retry = []

                while not self._sync_queue.empty():
                    try:
                        item = self._sync_queue.get_nowait()
                        self._pending_items.append(item)
                    except queue.Empty:
                        break

                # Try to sync pending items
                for item in list(self._pending_items):
                    if item.attempts >= self.MAX_RETRIES:
                        logger.warning(f"Max retries exceeded for {item.endpoint}")
                        self._pending_items.remove(item)
                        continue

                    # Run sync
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(self.sync_now(item))
                    loop.close()

                    if success:
                        self._pending_items.remove(item)
                    else:
                        # Exponential backoff
                        time.sleep(self.RETRY_DELAY * (2 ** item.attempts))

                # Check online status periodically
                if not self._is_online:
                    self._check_connectivity()

                # Save queue periodically
                self._save_queue()

                # Wait before next sync cycle
                time.sleep(self.SYNC_INTERVAL)

            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                time.sleep(5)

    def _check_connectivity(self):
        """Check if backend is reachable."""
        if not self._api_client:
            return

        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Try health check
            result = loop.run_until_complete(
                self._api_client.get("/health")
            )
            loop.close()

            self._update_online_status(True)

        except Exception:
            self._update_online_status(False)

    def _update_online_status(self, is_online: bool):
        """Update online status and notify listeners."""
        if self._is_online != is_online:
            self._is_online = is_online
            self._emit("online_status", is_online)
            logger.info(f"Online status: {'online' if is_online else 'offline'}")

    def _save_queue(self):
        """Persist queue to disk."""
        try:
            queue_file = os.path.join(self._cache_dir, "sync_queue.json")

            items_data = [
                {
                    "id": item.id,
                    "endpoint": item.endpoint,
                    "method": item.method,
                    "data": item.data,
                    "created_at": item.created_at.isoformat(),
                    "attempts": item.attempts,
                    "last_error": item.last_error,
                }
                for item in self._pending_items
            ]

            with open(queue_file, "w") as f:
                json.dump(items_data, f)

        except Exception as e:
            logger.error(f"Failed to save sync queue: {e}")

    def _load_queue(self):
        """Load persisted queue from disk."""
        try:
            queue_file = os.path.join(self._cache_dir, "sync_queue.json")

            if not os.path.exists(queue_file):
                return

            with open(queue_file, "r") as f:
                items_data = json.load(f)

            self._pending_items = [
                SyncItem(
                    id=item["id"],
                    endpoint=item["endpoint"],
                    method=item["method"],
                    data=item["data"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                    attempts=item["attempts"],
                    last_error=item.get("last_error"),
                )
                for item in items_data
            ]

            logger.info(f"Loaded {len(self._pending_items)} pending sync items")

        except Exception as e:
            logger.error(f"Failed to load sync queue: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get sync service status."""
        return {
            "is_running": self._is_running,
            "is_online": self._is_online,
            "pending_items": len(self._pending_items),
            "queue_size": self._sync_queue.qsize(),
            "has_api_client": self._api_client is not None,
        }

    def force_sync(self):
        """Force immediate sync attempt."""
        self._check_connectivity()
