"""
Offline storage service for ReadIn AI.

Provides SQLite-based local database for offline data persistence:
- Store meetings, transcripts, action items locally
- Queue pending syncs for when connectivity returns
- Manage storage limits and cleanup
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Synchronization status for offline items."""
    PENDING = "pending"          # Needs to be synced
    SYNCING = "syncing"          # Currently syncing
    SYNCED = "synced"            # Successfully synced
    CONFLICT = "conflict"        # Conflict detected
    FAILED = "failed"            # Sync failed (will retry)


class EntityType(Enum):
    """Types of entities that can be stored offline."""
    MEETING = "meeting"
    TRANSCRIPT = "transcript"
    CONVERSATION = "conversation"
    ACTION_ITEM = "action_item"
    COMMITMENT = "commitment"
    PARTICIPANT = "participant"
    SUMMARY = "summary"


@dataclass
class OfflineItem:
    """Represents an item stored offline."""
    id: str
    entity_type: str
    local_id: str
    remote_id: Optional[int]
    data: Dict[str, Any]
    sync_status: str
    created_at: datetime
    updated_at: datetime
    last_sync_attempt: Optional[datetime] = None
    sync_attempts: int = 0
    sync_error: Optional[str] = None
    checksum: Optional[str] = None


@dataclass
class PendingSync:
    """Represents a pending sync operation."""
    id: str
    entity_type: str
    operation: str  # "create", "update", "delete"
    local_id: str
    remote_id: Optional[int]
    data: Dict[str, Any]
    created_at: datetime
    priority: int = 0  # Higher = more important
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None


class OfflineStorage:
    """
    SQLite-based offline storage for ReadIn AI.

    Provides:
    - Local database for meetings, transcripts, action items
    - Sync queue management
    - Storage limit enforcement
    - Thread-safe operations
    """

    # Default settings
    DEFAULT_MAX_STORAGE_MB = 500
    DEFAULT_RETENTION_DAYS = 30
    MAX_SYNC_ATTEMPTS = 5

    # Schema version for migrations
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None, max_storage_mb: int = None):
        """
        Initialize offline storage.

        Args:
            db_path: Path to SQLite database file (default: ~/.readin/offline.db)
            max_storage_mb: Maximum storage size in MB
        """
        if db_path is None:
            base_dir = Path.home() / ".readin"
            base_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(base_dir / "offline.db")

        self._db_path = db_path
        self._max_storage_mb = max_storage_mb or self.DEFAULT_MAX_STORAGE_MB
        self._lock = threading.RLock()
        self._local_conn = threading.local()

        # Initialize database
        self._init_database()

        logger.info(f"Offline storage initialized: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local_conn, 'conn') or self._local_conn.conn is None:
            self._local_conn.conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._local_conn.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local_conn.conn.execute("PRAGMA foreign_keys = ON")
        return self._local_conn.conn

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_database(self):
        """Initialize database schema."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check schema version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            cursor.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            current_version = row['version'] if row else 0

            if current_version < self.SCHEMA_VERSION:
                self._migrate_schema(current_version)

            # Create main tables
            cursor.executescript("""
                -- Offline items storage
                CREATE TABLE IF NOT EXISTS offline_items (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    local_id TEXT NOT NULL,
                    remote_id INTEGER,
                    data TEXT NOT NULL,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    last_sync_attempt TIMESTAMP,
                    sync_attempts INTEGER DEFAULT 0,
                    sync_error TEXT,
                    checksum TEXT,
                    UNIQUE(entity_type, local_id)
                );

                CREATE INDEX IF NOT EXISTS idx_offline_items_type
                    ON offline_items(entity_type);
                CREATE INDEX IF NOT EXISTS idx_offline_items_sync_status
                    ON offline_items(sync_status);
                CREATE INDEX IF NOT EXISTS idx_offline_items_remote_id
                    ON offline_items(remote_id);

                -- Pending sync queue
                CREATE TABLE IF NOT EXISTS pending_sync (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    local_id TEXT NOT NULL,
                    remote_id INTEGER,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    priority INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    error TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_pending_sync_priority
                    ON pending_sync(priority DESC, created_at ASC);

                -- Meetings table (for quick queries)
                CREATE TABLE IF NOT EXISTS meetings (
                    local_id TEXT PRIMARY KEY,
                    remote_id INTEGER,
                    meeting_type TEXT,
                    title TEXT,
                    meeting_app TEXT,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_meetings_started
                    ON meetings(started_at DESC);

                -- Transcripts table
                CREATE TABLE IF NOT EXISTS transcripts (
                    local_id TEXT PRIMARY KEY,
                    meeting_local_id TEXT NOT NULL,
                    speaker_id TEXT,
                    speaker_name TEXT,
                    text TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_transcripts_meeting
                    ON transcripts(meeting_local_id);
                CREATE INDEX IF NOT EXISTS idx_transcripts_timestamp
                    ON transcripts(timestamp);

                -- Conversations (heard + AI response pairs)
                CREATE TABLE IF NOT EXISTS conversations (
                    local_id TEXT PRIMARY KEY,
                    meeting_local_id TEXT NOT NULL,
                    remote_id INTEGER,
                    heard_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    speaker TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_meeting
                    ON conversations(meeting_local_id);

                -- Action items
                CREATE TABLE IF NOT EXISTS action_items (
                    local_id TEXT PRIMARY KEY,
                    meeting_local_id TEXT,
                    remote_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    assignee TEXT,
                    due_date TIMESTAMP,
                    completed INTEGER DEFAULT 0,
                    completed_at TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id)
                        ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_action_items_completed
                    ON action_items(completed, due_date);

                -- Sync log for debugging
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    entity_type TEXT,
                    local_id TEXT,
                    operation TEXT,
                    status TEXT,
                    details TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp
                    ON sync_log(timestamp DESC);
            """)

            # Update schema version
            cursor.execute("""
                INSERT OR REPLACE INTO schema_version (version) VALUES (?)
            """, (self.SCHEMA_VERSION,))

            conn.commit()

    def _migrate_schema(self, from_version: int):
        """Migrate database schema from older version."""
        # Future migrations would go here
        logger.info(f"Migrating schema from version {from_version} to {self.SCHEMA_VERSION}")

    # ==================== Meeting Operations ====================

    def save_meeting(
        self,
        meeting_type: str = "general",
        title: Optional[str] = None,
        meeting_app: Optional[str] = None,
        remote_id: Optional[int] = None,
        started_at: Optional[datetime] = None
    ) -> str:
        """
        Save a meeting to local storage.

        Returns:
            Local meeting ID
        """
        local_id = str(uuid.uuid4())
        now = datetime.now()
        started = started_at or now

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO meetings
                (local_id, remote_id, meeting_type, title, meeting_app,
                 started_at, sync_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_id, remote_id, meeting_type, title, meeting_app,
                started, 'pending' if remote_id is None else 'synced',
                now, now
            ))

            # Queue for sync if not already synced
            if remote_id is None:
                self._queue_sync(
                    EntityType.MEETING.value,
                    "create",
                    local_id,
                    None,
                    {
                        "meeting_type": meeting_type,
                        "title": title,
                        "meeting_app": meeting_app,
                        "started_at": started.isoformat()
                    },
                    priority=10  # High priority
                )

        logger.debug(f"Meeting saved locally: {local_id}")
        return local_id

    def end_meeting(self, local_id: str) -> bool:
        """
        Mark a meeting as ended.

        Returns:
            True if meeting was found and updated
        """
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE meetings
                SET ended_at = ?, updated_at = ?, sync_status = 'pending'
                WHERE local_id = ?
            """, (now, now, local_id))

            if cursor.rowcount > 0:
                # Get remote_id if exists
                cursor.execute(
                    "SELECT remote_id FROM meetings WHERE local_id = ?",
                    (local_id,)
                )
                row = cursor.fetchone()
                remote_id = row['remote_id'] if row else None

                self._queue_sync(
                    EntityType.MEETING.value,
                    "update",
                    local_id,
                    remote_id,
                    {"ended_at": now.isoformat()},
                    priority=8
                )
                return True

        return False

    def get_meeting(self, local_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting by local ID."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM meetings WHERE local_id = ?
            """, (local_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_meetings(
        self,
        limit: int = 50,
        meeting_type: Optional[str] = None,
        include_ended: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recent meetings."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM meetings WHERE 1=1"
            params = []

            if meeting_type:
                query += " AND meeting_type = ?"
                params.append(meeting_type)

            if not include_ended:
                query += " AND ended_at IS NULL"

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_active_meeting(self) -> Optional[Dict[str, Any]]:
        """Get currently active meeting (not ended)."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM meetings
                WHERE ended_at IS NULL
                ORDER BY started_at DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            return dict(row) if row else None

    # ==================== Transcript Operations ====================

    def save_transcript(
        self,
        meeting_local_id: str,
        text: str,
        speaker_id: Optional[str] = None,
        speaker_name: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Save a transcript entry."""
        local_id = str(uuid.uuid4())
        now = datetime.now()
        ts = timestamp or now

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO transcripts
                (local_id, meeting_local_id, speaker_id, speaker_name, text,
                 timestamp, sync_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                local_id, meeting_local_id, speaker_id, speaker_name,
                text, ts, now
            ))

        return local_id

    def get_transcripts(
        self,
        meeting_local_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get transcripts for a meeting."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM transcripts
                WHERE meeting_local_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (meeting_local_id, limit))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== Conversation Operations ====================

    def save_conversation(
        self,
        meeting_local_id: str,
        heard_text: str,
        response_text: str,
        speaker: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Save a conversation (heard + response pair)."""
        local_id = str(uuid.uuid4())
        now = datetime.now()
        ts = timestamp or now

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations
                (local_id, meeting_local_id, heard_text, response_text,
                 speaker, timestamp, sync_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                local_id, meeting_local_id, heard_text, response_text,
                speaker, ts, now
            ))

            # Get meeting remote_id
            cursor.execute(
                "SELECT remote_id FROM meetings WHERE local_id = ?",
                (meeting_local_id,)
            )
            row = cursor.fetchone()
            meeting_remote_id = row['remote_id'] if row else None

            # Queue for sync
            self._queue_sync(
                EntityType.CONVERSATION.value,
                "create",
                local_id,
                None,
                {
                    "meeting_id": meeting_remote_id,
                    "meeting_local_id": meeting_local_id,
                    "heard_text": heard_text,
                    "response_text": response_text,
                    "speaker": speaker
                },
                priority=5
            )

        return local_id

    def get_conversations(
        self,
        meeting_local_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get conversations for a meeting."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM conversations
                WHERE meeting_local_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (meeting_local_id, limit))

            return [dict(row) for row in cursor.fetchall()]

    # ==================== Action Item Operations ====================

    def save_action_item(
        self,
        title: str,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        due_date: Optional[datetime] = None,
        meeting_local_id: Optional[str] = None
    ) -> str:
        """Save an action item."""
        local_id = str(uuid.uuid4())
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO action_items
                (local_id, meeting_local_id, title, description, assignee,
                 due_date, sync_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                local_id, meeting_local_id, title, description, assignee,
                due_date, now, now
            ))

            self._queue_sync(
                EntityType.ACTION_ITEM.value,
                "create",
                local_id,
                None,
                {
                    "title": title,
                    "description": description,
                    "assignee": assignee,
                    "due_date": due_date.isoformat() if due_date else None,
                    "meeting_local_id": meeting_local_id
                },
                priority=6
            )

        return local_id

    def complete_action_item(self, local_id: str) -> bool:
        """Mark an action item as completed."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE action_items
                SET completed = 1, completed_at = ?, updated_at = ?,
                    sync_status = 'pending'
                WHERE local_id = ?
            """, (now, now, local_id))

            if cursor.rowcount > 0:
                cursor.execute(
                    "SELECT remote_id FROM action_items WHERE local_id = ?",
                    (local_id,)
                )
                row = cursor.fetchone()
                remote_id = row['remote_id'] if row else None

                self._queue_sync(
                    EntityType.ACTION_ITEM.value,
                    "update",
                    local_id,
                    remote_id,
                    {"completed": True, "completed_at": now.isoformat()},
                    priority=7
                )
                return True

        return False

    def get_action_items(
        self,
        include_completed: bool = False,
        meeting_local_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get action items."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM action_items WHERE 1=1"
            params = []

            if not include_completed:
                query += " AND completed = 0"

            if meeting_local_id:
                query += " AND meeting_local_id = ?"
                params.append(meeting_local_id)

            query += " ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== Sync Queue Operations ====================

    def _queue_sync(
        self,
        entity_type: str,
        operation: str,
        local_id: str,
        remote_id: Optional[int],
        data: Dict[str, Any],
        priority: int = 0
    ):
        """Add item to sync queue (internal method)."""
        sync_id = str(uuid.uuid4())
        now = datetime.now()

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pending_sync
            (id, entity_type, operation, local_id, remote_id, data,
             created_at, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sync_id, entity_type, operation, local_id, remote_id,
            json.dumps(data), now, priority
        ))

    def get_pending_syncs(self, limit: int = 50) -> List[PendingSync]:
        """Get pending sync items ordered by priority."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM pending_sync
                WHERE attempts < ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            """, (self.MAX_SYNC_ATTEMPTS, limit))

            results = []
            for row in cursor.fetchall():
                results.append(PendingSync(
                    id=row['id'],
                    entity_type=row['entity_type'],
                    operation=row['operation'],
                    local_id=row['local_id'],
                    remote_id=row['remote_id'],
                    data=json.loads(row['data']),
                    created_at=row['created_at'],
                    priority=row['priority'],
                    attempts=row['attempts'],
                    last_attempt=row['last_attempt'],
                    error=row['error']
                ))

            return results

    def mark_sync_success(self, sync_id: str, remote_id: Optional[int] = None):
        """Mark a sync item as successfully synced."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            # Get sync item details
            cursor.execute(
                "SELECT entity_type, local_id FROM pending_sync WHERE id = ?",
                (sync_id,)
            )
            row = cursor.fetchone()

            if row:
                entity_type = row['entity_type']
                local_id = row['local_id']

                # Update corresponding table with remote_id and synced status
                table_map = {
                    'meeting': 'meetings',
                    'conversation': 'conversations',
                    'action_item': 'action_items'
                }

                table = table_map.get(entity_type)
                if table and remote_id:
                    cursor.execute(f"""
                        UPDATE {table}
                        SET remote_id = ?, sync_status = 'synced', updated_at = ?
                        WHERE local_id = ?
                    """, (remote_id, datetime.now(), local_id))

                # Remove from sync queue
                cursor.execute("DELETE FROM pending_sync WHERE id = ?", (sync_id,))

                # Log success
                self._log_sync(entity_type, local_id, "sync_success", "completed")

    def mark_sync_failure(self, sync_id: str, error: str):
        """Mark a sync item as failed."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE pending_sync
                SET attempts = attempts + 1, last_attempt = ?, error = ?
                WHERE id = ?
            """, (now, error, sync_id))

            # Get item for logging
            cursor.execute(
                "SELECT entity_type, local_id, attempts FROM pending_sync WHERE id = ?",
                (sync_id,)
            )
            row = cursor.fetchone()

            if row:
                self._log_sync(
                    row['entity_type'],
                    row['local_id'],
                    "sync_failure",
                    f"Attempt {row['attempts']}: {error}"
                )

    def get_sync_queue_count(self) -> int:
        """Get number of pending sync items."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM pending_sync")
            return cursor.fetchone()['count']

    def clear_completed_syncs(self):
        """Clear successfully synced items older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.DEFAULT_RETENTION_DAYS)

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            # Clear old sync logs
            cursor.execute(
                "DELETE FROM sync_log WHERE timestamp < ?",
                (cutoff,)
            )

    # ==================== ID Mapping ====================

    def update_remote_id(
        self,
        entity_type: str,
        local_id: str,
        remote_id: int
    ):
        """Update the remote ID for a locally stored item."""
        table_map = {
            'meeting': 'meetings',
            'conversation': 'conversations',
            'action_item': 'action_items'
        }

        table = table_map.get(entity_type)
        if not table:
            return

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE {table}
                SET remote_id = ?, sync_status = 'synced', updated_at = ?
                WHERE local_id = ?
            """, (remote_id, datetime.now(), local_id))

    def get_local_id_for_remote(
        self,
        entity_type: str,
        remote_id: int
    ) -> Optional[str]:
        """Get local ID for a remote entity."""
        table_map = {
            'meeting': 'meetings',
            'conversation': 'conversations',
            'action_item': 'action_items'
        }

        table = table_map.get(entity_type)
        if not table:
            return None

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT local_id FROM {table} WHERE remote_id = ?",
                (remote_id,)
            )
            row = cursor.fetchone()
            return row['local_id'] if row else None

    # ==================== Storage Management ====================

    def get_storage_size_mb(self) -> float:
        """Get current database size in MB."""
        try:
            return os.path.getsize(self._db_path) / (1024 * 1024)
        except OSError:
            return 0.0

    def is_storage_full(self) -> bool:
        """Check if storage limit is reached."""
        return self.get_storage_size_mb() >= self._max_storage_mb

    def cleanup_old_data(self, days: int = None):
        """
        Clean up old synced data to free space.

        Only removes fully synced items older than specified days.
        """
        if days is None:
            days = self.DEFAULT_RETENTION_DAYS

        cutoff = datetime.now() - timedelta(days=days)

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            # Delete old synced transcripts
            cursor.execute("""
                DELETE FROM transcripts
                WHERE sync_status = 'synced' AND created_at < ?
            """, (cutoff,))
            deleted_transcripts = cursor.rowcount

            # Delete old synced conversations
            cursor.execute("""
                DELETE FROM conversations
                WHERE sync_status = 'synced' AND created_at < ?
            """, (cutoff,))
            deleted_conversations = cursor.rowcount

            # Delete old synced meetings (cascades to transcripts/conversations)
            cursor.execute("""
                DELETE FROM meetings
                WHERE sync_status = 'synced' AND ended_at IS NOT NULL
                AND ended_at < ?
            """, (cutoff,))
            deleted_meetings = cursor.rowcount

            # Vacuum to reclaim space
            conn.execute("VACUUM")

            logger.info(
                f"Cleanup complete: {deleted_meetings} meetings, "
                f"{deleted_conversations} conversations, "
                f"{deleted_transcripts} transcripts removed"
            )

    def _log_sync(
        self,
        entity_type: str,
        local_id: str,
        operation: str,
        details: str
    ):
        """Log sync operation for debugging."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sync_log (timestamp, entity_type, local_id, operation, status, details)
            VALUES (?, ?, ?, ?, 'logged', ?)
        """, (datetime.now(), entity_type, local_id, operation, details))

    def get_sync_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent sync log entries."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM sync_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_status(self) -> Dict[str, Any]:
        """Get offline storage status."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Count items by type
            cursor.execute("SELECT COUNT(*) as count FROM meetings")
            meeting_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            conversation_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE completed = 0")
            pending_actions = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM pending_sync")
            pending_syncs = cursor.fetchone()['count']

            return {
                "database_path": self._db_path,
                "storage_size_mb": round(self.get_storage_size_mb(), 2),
                "max_storage_mb": self._max_storage_mb,
                "meeting_count": meeting_count,
                "conversation_count": conversation_count,
                "pending_action_items": pending_actions,
                "pending_syncs": pending_syncs,
                "schema_version": self.SCHEMA_VERSION
            }

    def close(self):
        """Close database connection."""
        if hasattr(self._local_conn, 'conn') and self._local_conn.conn:
            self._local_conn.conn.close()
            self._local_conn.conn = None


# Global instance (lazy initialization)
_offline_storage: Optional[OfflineStorage] = None


def get_offline_storage() -> OfflineStorage:
    """Get the global offline storage instance."""
    global _offline_storage
    if _offline_storage is None:
        _offline_storage = OfflineStorage()
    return _offline_storage
