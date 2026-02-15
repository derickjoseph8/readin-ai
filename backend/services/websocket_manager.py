"""
WebSocket connection manager for real-time updates.

Provides real-time notifications for:
- Meeting updates (started, ended, summary ready)
- Action item changes
- System notifications
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from config import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger("websocket")


class EventType(str, Enum):
    """WebSocket event types."""
    # Meeting events
    MEETING_STARTED = "meeting.started"
    MEETING_ENDED = "meeting.ended"
    MEETING_UPDATED = "meeting.updated"
    SUMMARY_READY = "meeting.summary_ready"

    # Conversation events
    CONVERSATION_ADDED = "conversation.added"
    TRANSCRIPTION_UPDATE = "transcription.update"

    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"

    # Notification events
    NOTIFICATION = "notification"

    # System events
    CONNECTION_ESTABLISHED = "connection.established"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    event: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp,
        })


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.

    Features:
    - User-based connection tracking
    - Room/channel support (for team features)
    - Authenticated connections
    - Broadcast and targeted messaging
    """

    def __init__(self):
        # User ID -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

        # Room/channel subscriptions: room_name -> Set of user IDs
        self.rooms: Dict[str, Set[int]] = {}

        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        metadata: Optional[Dict] = None,
    ):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: Authenticated user ID
            metadata: Optional connection metadata
        """
        await websocket.accept()

        # Add to user's connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        # Store connection metadata
        self.connection_info[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            **(metadata or {}),
        }

        logger.info(f"WebSocket connected: user={user_id}")

        # Send connection confirmation
        await self.send_personal_message(
            WebSocketMessage(
                event=EventType.CONNECTION_ESTABLISHED,
                data={"user_id": user_id, "message": "Connected successfully"},
            ),
            websocket,
        )

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        """
        info = self.connection_info.pop(websocket, {})
        user_id = info.get("user_id")

        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # Remove from all rooms
        for room_users in self.rooms.values():
            room_users.discard(user_id)

        logger.info(f"WebSocket disconnected: user={user_id}")

    async def send_personal_message(
        self,
        message: WebSocketMessage,
        websocket: WebSocket,
    ):
        """Send message to a specific WebSocket connection."""
        try:
            await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def send_to_user(
        self,
        message: WebSocketMessage,
        user_id: int,
    ):
        """Send message to all connections for a specific user."""
        connections = self.active_connections.get(user_id, set())
        for websocket in connections.copy():
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
                self.disconnect(websocket)

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude_users: Optional[Set[int]] = None,
    ):
        """Broadcast message to all connected users."""
        exclude = exclude_users or set()

        for user_id, connections in self.active_connections.items():
            if user_id in exclude:
                continue

            for websocket in connections.copy():
                try:
                    await websocket.send_text(message.to_json())
                except Exception:
                    self.disconnect(websocket)

    async def broadcast_to_room(
        self,
        message: WebSocketMessage,
        room: str,
        exclude_users: Optional[Set[int]] = None,
    ):
        """Broadcast message to all users in a room."""
        room_users = self.rooms.get(room, set())
        exclude = exclude_users or set()

        for user_id in room_users:
            if user_id in exclude:
                continue
            await self.send_to_user(message, user_id)

    def join_room(self, user_id: int, room: str):
        """Add user to a room for targeted broadcasts."""
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(user_id)
        logger.debug(f"User {user_id} joined room {room}")

    def leave_room(self, user_id: int, room: str):
        """Remove user from a room."""
        if room in self.rooms:
            self.rooms[room].discard(user_id)
            if not self.rooms[room]:
                del self.rooms[room]
        logger.debug(f"User {user_id} left room {room}")

    def get_user_count(self) -> int:
        """Get total number of connected users."""
        return len(self.active_connections)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())

    def is_user_online(self, user_id: int) -> bool:
        """Check if a user has active connections."""
        return user_id in self.active_connections and bool(self.active_connections[user_id])


# Global connection manager instance
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> Optional[int]:
    """
    Authenticate a WebSocket connection using JWT token.

    Token can be passed as:
    - Query parameter: ?token=xxx
    - First message after connection

    Returns user_id if authenticated, None otherwise.
    """
    # Try to get token from query params
    token = websocket.query_params.get("token")

    if not token:
        # Wait for token in first message
        try:
            data = await websocket.receive_json()
            token = data.get("token")
        except Exception:
            return None

    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        return user_id
    except JWTError:
        return None


# =============================================================================
# HELPER FUNCTIONS FOR SENDING EVENTS
# =============================================================================

async def notify_meeting_started(user_id: int, meeting_data: Dict):
    """Notify user that a meeting has started."""
    await manager.send_to_user(
        WebSocketMessage(
            event=EventType.MEETING_STARTED,
            data=meeting_data,
        ),
        user_id,
    )


async def notify_meeting_ended(user_id: int, meeting_data: Dict):
    """Notify user that a meeting has ended."""
    await manager.send_to_user(
        WebSocketMessage(
            event=EventType.MEETING_ENDED,
            data=meeting_data,
        ),
        user_id,
    )


async def notify_summary_ready(user_id: int, meeting_id: int, summary: Dict):
    """Notify user that a meeting summary is ready."""
    await manager.send_to_user(
        WebSocketMessage(
            event=EventType.SUMMARY_READY,
            data={
                "meeting_id": meeting_id,
                "summary": summary,
            },
        ),
        user_id,
    )


async def notify_task_update(user_id: int, task_data: Dict, event_type: EventType):
    """Notify user about task changes."""
    await manager.send_to_user(
        WebSocketMessage(
            event=event_type,
            data=task_data,
        ),
        user_id,
    )


async def send_notification(user_id: int, title: str, message: str, data: Optional[Dict] = None):
    """Send a general notification to a user."""
    await manager.send_to_user(
        WebSocketMessage(
            event=EventType.NOTIFICATION,
            data={
                "title": title,
                "message": message,
                **(data or {}),
            },
        ),
        user_id,
    )
