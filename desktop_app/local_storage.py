"""
Local Storage for ReadIn AI Desktop App.

SQLite-based local database for:
- Caching meetings, conversations, action items
- Storing user preferences
- Managing pending sync operations
- Conflict tracking and resolution data
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """Cache expiration policies."""
    NEVER_EXPIRE = "never"
    SHORT = "short"       # 5 minutes
    MEDIUM = "medium"     # 1 hour
    LONG = "long"         # 24 hours
    SESSION = "session"   # Until app restart


class SyncOperation(Enum):
    """Types of sync operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ConflictStrategy(Enum):
    """Conflict resolution strategies."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    NEWEST_WINS = "newest_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class CachedItem:
    """Represents a cached item."""
    key: str
    value: Any
    entity_type: str
    expires_at: Optional[datetime] = None
    checksum: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)


@dataclass
class PendingSyncOperation:
    """Represents a pending sync operation."""
    id: str
    entity_type: str
    operation: str
    entity_id: str
    remote_id: Optional[int]
    data: Dict[str, Any]
    priority: int
    created_at: datetime
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    error: Optional[str] = None
    conflict_data: Optional[Dict[str, Any]] = None
    checksum: Optional[str] = None


@dataclass
class ConflictRecord:
    """Records a sync conflict for resolution."""
    id: str
    entity_type: str
    entity_id: str
    local_data: Dict[str, Any]
    server_data: Dict[str, Any]
    local_checksum: str
    server_checksum: str
    created_at: datetime
    resolved: bool = False
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


class LocalStorage:
    """
    SQLite-based local storage for ReadIn AI.

    Provides:
    - Local caching of API data with expiration policies
    - User preference storage
    - Sync queue management with conflict tracking
    - Thread-safe operations with connection pooling
    """

    # Schema version for migrations
    SCHEMA_VERSION = 2

    # Default settings
    DEFAULT_CACHE_SIZE_MB = 200
    MAX_SYNC_RETRIES = 5

    # Cache expiration times (seconds)
    CACHE_DURATIONS = {
        CachePolicy.SHORT: 300,         # 5 minutes
        CachePolicy.MEDIUM: 3600,       # 1 hour
        CachePolicy.LONG: 86400,        # 24 hours
        CachePolicy.SESSION: None,      # No automatic expiry
        CachePolicy.NEVER_EXPIRE: None,
    }

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_cache_size_mb: int = None
    ):
        """
        Initialize local storage.

        Args:
            db_path: Path to SQLite database file
            max_cache_size_mb: Maximum cache size in MB
        """
        if db_path is None:
            base_dir = Path.home() / ".readin" / "data"
            base_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(base_dir / "local_cache.db")

        self._db_path = db_path
        self._max_cache_size_mb = max_cache_size_mb or self.DEFAULT_CACHE_SIZE_MB
        self._lock = threading.RLock()
        self._local_conn = threading.local()
        self._session_start = datetime.now()

        # Initialize database
        self._init_database()

        logger.info(f"Local storage initialized: {db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local_conn, 'conn') or self._local_conn.conn is None:
            self._local_conn.conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._local_conn.conn.row_factory = sqlite3.Row
            # Enable foreign keys and WAL mode for better concurrency
            self._local_conn.conn.execute("PRAGMA foreign_keys = ON")
            self._local_conn.conn.execute("PRAGMA journal_mode = WAL")
            self._local_conn.conn.execute("PRAGMA synchronous = NORMAL")
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
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            cursor.execute("SELECT value FROM schema_info WHERE key = 'version'")
            row = cursor.fetchone()
            current_version = int(row['value']) if row else 0

            if current_version < self.SCHEMA_VERSION:
                self._migrate_schema(cursor, current_version)

            # Create tables
            cursor.executescript("""
                -- Generic cache table
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_cache_type ON cache(entity_type);
                CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);

                -- User preferences
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                -- Meetings cache
                CREATE TABLE IF NOT EXISTS meetings (
                    local_id TEXT PRIMARY KEY,
                    remote_id INTEGER UNIQUE,
                    meeting_type TEXT,
                    title TEXT,
                    meeting_app TEXT,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    summary_text TEXT,
                    key_points TEXT,
                    participant_count INTEGER,
                    sync_status TEXT DEFAULT 'pending',
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_meetings_remote ON meetings(remote_id);
                CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
                CREATE INDEX IF NOT EXISTS idx_meetings_sync ON meetings(sync_status);
                CREATE INDEX IF NOT EXISTS idx_meetings_started ON meetings(started_at DESC);

                -- Conversations cache
                CREATE TABLE IF NOT EXISTS conversations (
                    local_id TEXT PRIMARY KEY,
                    remote_id INTEGER UNIQUE,
                    meeting_local_id TEXT,
                    meeting_remote_id INTEGER,
                    heard_text TEXT NOT NULL,
                    response_text TEXT,
                    speaker TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    sentiment TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_conv_meeting ON conversations(meeting_local_id);
                CREATE INDEX IF NOT EXISTS idx_conv_remote ON conversations(remote_id);
                CREATE INDEX IF NOT EXISTS idx_conv_sync ON conversations(sync_status);

                -- Action items cache
                CREATE TABLE IF NOT EXISTS action_items (
                    local_id TEXT PRIMARY KEY,
                    remote_id INTEGER UNIQUE,
                    meeting_local_id TEXT,
                    meeting_remote_id INTEGER,
                    description TEXT NOT NULL,
                    assignee TEXT,
                    assignee_role TEXT,
                    due_date TIMESTAMP,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    completed_at TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_action_meeting ON action_items(meeting_local_id);
                CREATE INDEX IF NOT EXISTS idx_action_status ON action_items(status);
                CREATE INDEX IF NOT EXISTS idx_action_due ON action_items(due_date);
                CREATE INDEX IF NOT EXISTS idx_action_sync ON action_items(sync_status);

                -- Commitments cache
                CREATE TABLE IF NOT EXISTS commitments (
                    local_id TEXT PRIMARY KEY,
                    remote_id INTEGER UNIQUE,
                    meeting_local_id TEXT,
                    meeting_remote_id INTEGER,
                    description TEXT NOT NULL,
                    due_date TIMESTAMP,
                    context TEXT,
                    status TEXT DEFAULT 'pending',
                    completed_at TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_local_id) REFERENCES meetings(local_id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_commit_meeting ON commitments(meeting_local_id);
                CREATE INDEX IF NOT EXISTS idx_commit_status ON commitments(status);
                CREATE INDEX IF NOT EXISTS idx_commit_sync ON commitments(sync_status);

                -- Sync queue
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    remote_id INTEGER,
                    data TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    attempts INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    next_retry TIMESTAMP,
                    error TEXT,
                    conflict_data TEXT,
                    checksum TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sync_priority ON sync_queue(priority DESC, created_at ASC);
                CREATE INDEX IF NOT EXISTS idx_sync_retry ON sync_queue(next_retry);
                CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_queue(entity_type, entity_id);

                -- Conflicts
                CREATE TABLE IF NOT EXISTS conflicts (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    local_data TEXT NOT NULL,
                    server_data TEXT NOT NULL,
                    local_checksum TEXT NOT NULL,
                    server_checksum TEXT NOT NULL,
                    resolved INTEGER DEFAULT 0,
                    resolution TEXT,
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_conflicts_resolved ON conflicts(resolved);
                CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON conflicts(entity_type, entity_id);

                -- Sync log for debugging
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    entity_type TEXT,
                    entity_id TEXT,
                    operation TEXT,
                    status TEXT,
                    details TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_sync_log_time ON sync_log(timestamp DESC);

                -- ID mapping (local to remote)
                CREATE TABLE IF NOT EXISTS id_mapping (
                    entity_type TEXT NOT NULL,
                    local_id TEXT NOT NULL,
                    remote_id INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (entity_type, local_id)
                );
                CREATE INDEX IF NOT EXISTS idx_mapping_remote ON id_mapping(entity_type, remote_id);
            """)

            # Update schema version
            cursor.execute("""
                INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', ?)
            """, (str(self.SCHEMA_VERSION),))

            conn.commit()

    def _migrate_schema(self, cursor, from_version: int):
        """Migrate database schema."""
        logger.info(f"Migrating schema from version {from_version} to {self.SCHEMA_VERSION}")

        if from_version < 1:
            # Initial schema - nothing to migrate
            pass

        if from_version < 2:
            # Add checksum columns if missing
            try:
                cursor.execute("ALTER TABLE meetings ADD COLUMN checksum TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

    # ==================== Cache Operations ====================

    def cache_set(
        self,
        key: str,
        value: Any,
        entity_type: str = "general",
        policy: CachePolicy = CachePolicy.MEDIUM
    ) -> bool:
        """
        Store a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            entity_type: Type of entity for grouping
            policy: Cache expiration policy

        Returns:
            True if successful
        """
        now = datetime.now()
        duration = self.CACHE_DURATIONS.get(policy)
        expires_at = now + timedelta(seconds=duration) if duration else None

        value_json = json.dumps(value, default=str)
        checksum = self._compute_checksum(value_json)

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cache
                (key, entity_type, value, expires_at, checksum, created_at, accessed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (key, entity_type, value_json, expires_at, checksum, now, now))

        return True

    def cache_get(
        self,
        key: str,
        default: Any = None,
        update_accessed: bool = True
    ) -> Any:
        """
        Get a value from cache.

        Args:
            key: Cache key
            default: Default value if not found or expired
            update_accessed: Update last accessed time

        Returns:
            Cached value or default
        """
        now = datetime.now()

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT value, expires_at FROM cache
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (key, now))

            row = cursor.fetchone()
            if not row:
                return default

            if update_accessed:
                cursor.execute(
                    "UPDATE cache SET accessed_at = ? WHERE key = ?",
                    (now, key)
                )
                conn.commit()

            try:
                return json.loads(row['value'])
            except json.JSONDecodeError:
                return default

    def cache_delete(self, key: str) -> bool:
        """Delete a cache entry."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
            return cursor.rowcount > 0

    def cache_clear(self, entity_type: Optional[str] = None):
        """Clear cache entries."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute("DELETE FROM cache WHERE entity_type = ?", (entity_type,))
            else:
                cursor.execute("DELETE FROM cache")

    def cache_cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,)
            )
            return cursor.rowcount

    # ==================== Preferences ====================

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = cursor.fetchone()

            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default

    def set_preference(self, key: str, value: Any) -> bool:
        """Set a user preference."""
        value_json = json.dumps(value, default=str)

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_json, datetime.now()))
            return True

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM preferences")

            result = {}
            for row in cursor.fetchall():
                try:
                    result[row['key']] = json.loads(row['value'])
                except json.JSONDecodeError:
                    result[row['key']] = row['value']
            return result

    def delete_preference(self, key: str) -> bool:
        """Delete a preference."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM preferences WHERE key = ?", (key,))
            return cursor.rowcount > 0

    # ==================== Meeting Operations ====================

    def save_meeting(
        self,
        meeting_type: str = "general",
        title: Optional[str] = None,
        meeting_app: Optional[str] = None,
        remote_id: Optional[int] = None,
        started_at: Optional[datetime] = None,
        local_id: Optional[str] = None
    ) -> str:
        """
        Save a meeting to local storage.

        Returns:
            Local meeting ID
        """
        if local_id is None:
            local_id = str(uuid.uuid4())

        now = datetime.now()
        started = started_at or now
        sync_status = 'synced' if remote_id else 'pending'

        data = {
            "meeting_type": meeting_type,
            "title": title,
            "meeting_app": meeting_app,
            "started_at": started.isoformat()
        }
        checksum = self._compute_checksum(json.dumps(data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO meetings
                (local_id, remote_id, meeting_type, title, meeting_app,
                 started_at, sync_status, checksum, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_id, remote_id, meeting_type, title, meeting_app,
                started, sync_status, checksum, now, now
            ))

            # Queue for sync if not synced
            if not remote_id:
                self._add_to_sync_queue(
                    entity_type="meeting",
                    operation=SyncOperation.CREATE.value,
                    entity_id=local_id,
                    data=data,
                    priority=10,
                    checksum=checksum
                )

        logger.debug(f"Meeting saved: {local_id}")
        return local_id

    def end_meeting(self, local_id: str) -> bool:
        """Mark a meeting as ended."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE meetings
                SET ended_at = ?, status = 'ended', sync_status = 'pending', updated_at = ?
                WHERE local_id = ?
            """, (now, now, local_id))

            if cursor.rowcount > 0:
                cursor.execute(
                    "SELECT remote_id FROM meetings WHERE local_id = ?",
                    (local_id,)
                )
                row = cursor.fetchone()
                remote_id = row['remote_id'] if row else None

                self._add_to_sync_queue(
                    entity_type="meeting",
                    operation=SyncOperation.UPDATE.value,
                    entity_id=local_id,
                    remote_id=remote_id,
                    data={"ended_at": now.isoformat()},
                    priority=8
                )
                return True

        return False

    def get_meeting(self, local_id: str) -> Optional[Dict[str, Any]]:
        """Get meeting by local ID."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings WHERE local_id = ?", (local_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_meeting_by_remote_id(self, remote_id: int) -> Optional[Dict[str, Any]]:
        """Get meeting by remote ID."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings WHERE remote_id = ?", (remote_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_meetings(
        self,
        limit: int = 50,
        meeting_type: Optional[str] = None,
        status: Optional[str] = None,
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

            if status:
                query += " AND status = ?"
                params.append(status)

            if not include_ended:
                query += " AND status = 'active'"

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_active_meeting(self) -> Optional[Dict[str, Any]]:
        """Get currently active meeting."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM meetings
                WHERE status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_meeting_summary(
        self,
        local_id: str,
        summary_text: str,
        key_points: Optional[List[str]] = None
    ) -> bool:
        """Update meeting summary."""
        now = datetime.now()
        key_points_json = json.dumps(key_points) if key_points else None

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE meetings
                SET summary_text = ?, key_points = ?, updated_at = ?
                WHERE local_id = ?
            """, (summary_text, key_points_json, now, local_id))
            return cursor.rowcount > 0

    # ==================== Conversation Operations ====================

    def save_conversation(
        self,
        meeting_local_id: str,
        heard_text: str,
        response_text: str = "",
        speaker: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        remote_id: Optional[int] = None
    ) -> str:
        """Save a conversation entry."""
        local_id = str(uuid.uuid4())
        now = datetime.now()
        ts = timestamp or now
        sync_status = 'synced' if remote_id else 'pending'

        # Get meeting remote_id
        meeting_remote_id = None
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT remote_id FROM meetings WHERE local_id = ?",
                (meeting_local_id,)
            )
            row = cursor.fetchone()
            if row:
                meeting_remote_id = row['remote_id']

        data = {
            "meeting_local_id": meeting_local_id,
            "meeting_id": meeting_remote_id,
            "heard_text": heard_text,
            "response_text": response_text,
            "speaker": speaker
        }
        checksum = self._compute_checksum(json.dumps(data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO conversations
                (local_id, remote_id, meeting_local_id, meeting_remote_id,
                 heard_text, response_text, speaker, timestamp, sync_status, checksum, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_id, remote_id, meeting_local_id, meeting_remote_id,
                heard_text, response_text, speaker, ts, sync_status, checksum, now
            ))

            if not remote_id:
                self._add_to_sync_queue(
                    entity_type="conversation",
                    operation=SyncOperation.CREATE.value,
                    entity_id=local_id,
                    data=data,
                    priority=5,
                    checksum=checksum
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
        description: str,
        assignee: Optional[str] = None,
        assignee_role: Optional[str] = None,
        due_date: Optional[datetime] = None,
        priority: str = "medium",
        meeting_local_id: Optional[str] = None,
        remote_id: Optional[int] = None
    ) -> str:
        """Save an action item."""
        local_id = str(uuid.uuid4())
        now = datetime.now()
        sync_status = 'synced' if remote_id else 'pending'

        # Get meeting remote_id
        meeting_remote_id = None
        if meeting_local_id:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT remote_id FROM meetings WHERE local_id = ?",
                    (meeting_local_id,)
                )
                row = cursor.fetchone()
                if row:
                    meeting_remote_id = row['remote_id']

        data = {
            "description": description,
            "assignee": assignee,
            "assignee_role": assignee_role,
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority,
            "meeting_local_id": meeting_local_id,
            "meeting_id": meeting_remote_id
        }
        checksum = self._compute_checksum(json.dumps(data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO action_items
                (local_id, remote_id, meeting_local_id, meeting_remote_id,
                 description, assignee, assignee_role, due_date, priority,
                 sync_status, checksum, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_id, remote_id, meeting_local_id, meeting_remote_id,
                description, assignee, assignee_role, due_date, priority,
                sync_status, checksum, now, now
            ))

            if not remote_id:
                self._add_to_sync_queue(
                    entity_type="action_item",
                    operation=SyncOperation.CREATE.value,
                    entity_id=local_id,
                    data=data,
                    priority=7,
                    checksum=checksum
                )

        return local_id

    def complete_action_item(self, local_id: str) -> bool:
        """Mark action item as complete."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE action_items
                SET status = 'completed', completed_at = ?, sync_status = 'pending', updated_at = ?
                WHERE local_id = ?
            """, (now, now, local_id))

            if cursor.rowcount > 0:
                cursor.execute(
                    "SELECT remote_id FROM action_items WHERE local_id = ?",
                    (local_id,)
                )
                row = cursor.fetchone()
                remote_id = row['remote_id'] if row else None

                self._add_to_sync_queue(
                    entity_type="action_item",
                    operation=SyncOperation.UPDATE.value,
                    entity_id=local_id,
                    remote_id=remote_id,
                    data={"completed": True, "completed_at": now.isoformat()},
                    priority=6
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
                query += " AND status != 'completed'"

            if meeting_local_id:
                query += " AND meeting_local_id = ?"
                params.append(meeting_local_id)

            query += " ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== Commitment Operations ====================

    def save_commitment(
        self,
        description: str,
        due_date: Optional[datetime] = None,
        context: Optional[str] = None,
        meeting_local_id: Optional[str] = None,
        remote_id: Optional[int] = None
    ) -> str:
        """Save a commitment."""
        local_id = str(uuid.uuid4())
        now = datetime.now()
        sync_status = 'synced' if remote_id else 'pending'

        meeting_remote_id = None
        if meeting_local_id:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT remote_id FROM meetings WHERE local_id = ?",
                    (meeting_local_id,)
                )
                row = cursor.fetchone()
                if row:
                    meeting_remote_id = row['remote_id']

        data = {
            "description": description,
            "due_date": due_date.isoformat() if due_date else None,
            "context": context,
            "meeting_local_id": meeting_local_id,
            "meeting_id": meeting_remote_id
        }
        checksum = self._compute_checksum(json.dumps(data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO commitments
                (local_id, remote_id, meeting_local_id, meeting_remote_id,
                 description, due_date, context, sync_status, checksum, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                local_id, remote_id, meeting_local_id, meeting_remote_id,
                description, due_date, context, sync_status, checksum, now, now
            ))

            if not remote_id:
                self._add_to_sync_queue(
                    entity_type="commitment",
                    operation=SyncOperation.CREATE.value,
                    entity_id=local_id,
                    data=data,
                    priority=6,
                    checksum=checksum
                )

        return local_id

    def get_commitments(
        self,
        include_completed: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get commitments."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM commitments WHERE 1=1"
            params = []

            if not include_completed:
                query += " AND status != 'completed'"

            query += " ORDER BY due_date ASC NULLS LAST, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # ==================== Sync Queue Operations ====================

    def _add_to_sync_queue(
        self,
        entity_type: str,
        operation: str,
        entity_id: str,
        data: Dict[str, Any],
        priority: int = 5,
        remote_id: Optional[int] = None,
        checksum: Optional[str] = None
    ):
        """Add item to sync queue (internal)."""
        sync_id = str(uuid.uuid4())
        now = datetime.now()

        conn = self._get_connection()
        cursor = conn.cursor()

        # Check for existing entry with same entity
        cursor.execute("""
            SELECT id FROM sync_queue
            WHERE entity_type = ? AND entity_id = ? AND operation = ?
        """, (entity_type, entity_id, operation))

        existing = cursor.fetchone()
        if existing:
            # Update existing entry
            cursor.execute("""
                UPDATE sync_queue
                SET data = ?, priority = ?, checksum = ?, remote_id = ?
                WHERE id = ?
            """, (json.dumps(data), priority, checksum, remote_id, existing['id']))
        else:
            # Insert new entry
            cursor.execute("""
                INSERT INTO sync_queue
                (id, entity_type, operation, entity_id, remote_id, data, priority, checksum, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sync_id, entity_type, operation, entity_id, remote_id,
                json.dumps(data), priority, checksum, now
            ))

    def add_sync_operation(
        self,
        entity_type: str,
        operation: SyncOperation,
        entity_id: str,
        data: Dict[str, Any],
        priority: int = 5,
        remote_id: Optional[int] = None
    ) -> str:
        """Add a sync operation to the queue."""
        checksum = self._compute_checksum(json.dumps(data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            self._add_to_sync_queue(
                entity_type=entity_type,
                operation=operation.value,
                entity_id=entity_id,
                data=data,
                priority=priority,
                remote_id=remote_id,
                checksum=checksum
            )

        return entity_id

    def get_pending_syncs(
        self,
        limit: int = 50,
        entity_type: Optional[str] = None
    ) -> List[PendingSyncOperation]:
        """Get pending sync operations."""
        now = datetime.now()

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = """
                SELECT * FROM sync_queue
                WHERE attempts < ?
                AND (next_retry IS NULL OR next_retry <= ?)
            """
            params = [self.MAX_SYNC_RETRIES, now]

            if entity_type:
                query += " AND entity_type = ?"
                params.append(entity_type)

            query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append(PendingSyncOperation(
                    id=row['id'],
                    entity_type=row['entity_type'],
                    operation=row['operation'],
                    entity_id=row['entity_id'],
                    remote_id=row['remote_id'],
                    data=json.loads(row['data']),
                    priority=row['priority'],
                    created_at=row['created_at'],
                    attempts=row['attempts'],
                    last_attempt=row['last_attempt'],
                    next_retry=row['next_retry'],
                    error=row['error'],
                    conflict_data=json.loads(row['conflict_data']) if row['conflict_data'] else None,
                    checksum=row['checksum']
                ))

            return results

    def mark_sync_success(
        self,
        sync_id: str,
        remote_id: Optional[int] = None
    ):
        """Mark sync operation as successful."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            # Get sync item details
            cursor.execute(
                "SELECT entity_type, entity_id FROM sync_queue WHERE id = ?",
                (sync_id,)
            )
            row = cursor.fetchone()

            if row:
                entity_type = row['entity_type']
                entity_id = row['entity_id']

                # Update entity with remote_id
                table_map = {
                    'meeting': 'meetings',
                    'conversation': 'conversations',
                    'action_item': 'action_items',
                    'commitment': 'commitments'
                }

                table = table_map.get(entity_type)
                if table and remote_id:
                    cursor.execute(f"""
                        UPDATE {table}
                        SET remote_id = ?, sync_status = 'synced', updated_at = ?
                        WHERE local_id = ?
                    """, (remote_id, datetime.now(), entity_id))

                    # Add to ID mapping
                    cursor.execute("""
                        INSERT OR REPLACE INTO id_mapping (entity_type, local_id, remote_id, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (entity_type, entity_id, remote_id, datetime.now()))

                # Remove from sync queue
                cursor.execute("DELETE FROM sync_queue WHERE id = ?", (sync_id,))

                # Log success
                self._log_sync(entity_type, entity_id, "success", "Synced successfully")

    def mark_sync_failure(
        self,
        sync_id: str,
        error: str,
        conflict_data: Optional[Dict[str, Any]] = None
    ):
        """Mark sync operation as failed."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT attempts FROM sync_queue WHERE id = ?", (sync_id,))
            row = cursor.fetchone()

            if row:
                attempts = row['attempts'] + 1
                # Exponential backoff: 30s, 1m, 2m, 4m, 8m
                backoff_seconds = min(30 * (2 ** row['attempts']), 480)
                next_retry = now + timedelta(seconds=backoff_seconds)

                conflict_json = json.dumps(conflict_data) if conflict_data else None

                cursor.execute("""
                    UPDATE sync_queue
                    SET attempts = ?, last_attempt = ?, next_retry = ?, error = ?, conflict_data = ?
                    WHERE id = ?
                """, (attempts, now, next_retry, error, conflict_json, sync_id))

                # Log failure
                cursor.execute(
                    "SELECT entity_type, entity_id FROM sync_queue WHERE id = ?",
                    (sync_id,)
                )
                info = cursor.fetchone()
                if info:
                    self._log_sync(
                        info['entity_type'],
                        info['entity_id'],
                        "failure",
                        f"Attempt {attempts}: {error}"
                    )

    def get_sync_queue_count(self) -> int:
        """Get number of pending sync items."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM sync_queue WHERE attempts < ?",
                (self.MAX_SYNC_RETRIES,)
            )
            return cursor.fetchone()['count']

    def clear_sync_queue(self, entity_type: Optional[str] = None):
        """Clear sync queue."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute("DELETE FROM sync_queue WHERE entity_type = ?", (entity_type,))
            else:
                cursor.execute("DELETE FROM sync_queue")

    # ==================== Conflict Operations ====================

    def record_conflict(
        self,
        entity_type: str,
        entity_id: str,
        local_data: Dict[str, Any],
        server_data: Dict[str, Any]
    ) -> str:
        """Record a sync conflict."""
        conflict_id = str(uuid.uuid4())
        now = datetime.now()

        local_checksum = self._compute_checksum(json.dumps(local_data, sort_keys=True))
        server_checksum = self._compute_checksum(json.dumps(server_data, sort_keys=True))

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conflicts
                (id, entity_type, entity_id, local_data, server_data,
                 local_checksum, server_checksum, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conflict_id, entity_type, entity_id,
                json.dumps(local_data), json.dumps(server_data),
                local_checksum, server_checksum, now
            ))

        return conflict_id

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictStrategy,
        resolved_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Resolve a recorded conflict."""
        now = datetime.now()

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE conflicts
                SET resolved = 1, resolution = ?, resolved_at = ?
                WHERE id = ?
            """, (resolution.value, now, conflict_id))

            return cursor.rowcount > 0

    def get_unresolved_conflicts(self) -> List[ConflictRecord]:
        """Get unresolved conflicts."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conflicts
                WHERE resolved = 0
                ORDER BY created_at DESC
            """)

            results = []
            for row in cursor.fetchall():
                results.append(ConflictRecord(
                    id=row['id'],
                    entity_type=row['entity_type'],
                    entity_id=row['entity_id'],
                    local_data=json.loads(row['local_data']),
                    server_data=json.loads(row['server_data']),
                    local_checksum=row['local_checksum'],
                    server_checksum=row['server_checksum'],
                    created_at=row['created_at'],
                    resolved=bool(row['resolved']),
                    resolution=row['resolution'],
                    resolved_at=row['resolved_at']
                ))

            return results

    # ==================== ID Mapping ====================

    def get_remote_id(self, entity_type: str, local_id: str) -> Optional[int]:
        """Get remote ID for a local entity."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT remote_id FROM id_mapping
                WHERE entity_type = ? AND local_id = ?
            """, (entity_type, local_id))
            row = cursor.fetchone()
            return row['remote_id'] if row else None

    def get_local_id(self, entity_type: str, remote_id: int) -> Optional[str]:
        """Get local ID for a remote entity."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT local_id FROM id_mapping
                WHERE entity_type = ? AND remote_id = ?
            """, (entity_type, remote_id))
            row = cursor.fetchone()
            return row['local_id'] if row else None

    def set_id_mapping(self, entity_type: str, local_id: str, remote_id: int):
        """Set ID mapping."""
        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO id_mapping (entity_type, local_id, remote_id, created_at)
                VALUES (?, ?, ?, ?)
            """, (entity_type, local_id, remote_id, datetime.now()))

    # ==================== Utility Methods ====================

    def _compute_checksum(self, data: str) -> str:
        """Compute MD5 checksum for conflict detection."""
        return hashlib.md5(data.encode()).hexdigest()

    def _log_sync(
        self,
        entity_type: str,
        entity_id: str,
        status: str,
        details: str
    ):
        """Log sync operation."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_log (timestamp, entity_type, entity_id, operation, status, details)
            VALUES (?, ?, ?, 'sync', ?, ?)
        """, (datetime.now(), entity_type, entity_id, status, details))

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

    def get_storage_size_mb(self) -> float:
        """Get database size in MB."""
        try:
            return os.path.getsize(self._db_path) / (1024 * 1024)
        except OSError:
            return 0.0

    def cleanup_old_data(self, days: int = 30):
        """Clean up old synced data."""
        cutoff = datetime.now() - timedelta(days=days)

        with self._lock, self._transaction() as conn:
            cursor = conn.cursor()

            # Clear old sync logs
            cursor.execute("DELETE FROM sync_log WHERE timestamp < ?", (cutoff,))

            # Clear old resolved conflicts
            cursor.execute(
                "DELETE FROM conflicts WHERE resolved = 1 AND resolved_at < ?",
                (cutoff,)
            )

            # Clear expired cache
            self.cache_cleanup_expired()

            # Vacuum
            conn.execute("VACUUM")

    def get_status(self) -> Dict[str, Any]:
        """Get storage status."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM meetings")
            meeting_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM conversations")
            conversation_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM action_items WHERE status != 'completed'")
            pending_actions = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM sync_queue")
            pending_syncs = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM conflicts WHERE resolved = 0")
            unresolved_conflicts = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM cache")
            cache_entries = cursor.fetchone()['count']

            return {
                "database_path": self._db_path,
                "storage_size_mb": round(self.get_storage_size_mb(), 2),
                "max_storage_mb": self._max_cache_size_mb,
                "meeting_count": meeting_count,
                "conversation_count": conversation_count,
                "pending_action_items": pending_actions,
                "pending_syncs": pending_syncs,
                "unresolved_conflicts": unresolved_conflicts,
                "cache_entries": cache_entries,
                "schema_version": self.SCHEMA_VERSION
            }

    def close(self):
        """Close database connection."""
        if hasattr(self._local_conn, 'conn') and self._local_conn.conn:
            self._local_conn.conn.close()
            self._local_conn.conn = None


# Global instance
_local_storage: Optional[LocalStorage] = None


def get_local_storage() -> LocalStorage:
    """Get global local storage instance."""
    global _local_storage
    if _local_storage is None:
        _local_storage = LocalStorage()
    return _local_storage
