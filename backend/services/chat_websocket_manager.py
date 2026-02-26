"""
WebSocket connection manager for real-time chat support.

Provides real-time messaging for the support chat system:
- Customer to agent messaging
- Agent presence/typing indicators
- Chat status updates (waiting -> active -> ended)
- Queue position updates
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from fastapi import WebSocket
from jose import JWTError, jwt

from config import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger("chat_websocket")


class ChatEventType(str, Enum):
    """WebSocket event types for chat system."""
    # Connection events
    CONNECTION_ESTABLISHED = "chat.connection_established"
    CONNECTION_ERROR = "chat.connection_error"

    # Message events
    NEW_MESSAGE = "chat.new_message"
    MESSAGE_READ = "chat.message_read"
    TYPING_START = "chat.typing_start"
    TYPING_STOP = "chat.typing_stop"

    # Session events
    SESSION_STATUS_CHANGED = "chat.session_status_changed"
    AGENT_JOINED = "chat.agent_joined"
    AGENT_LEFT = "chat.agent_left"
    QUEUE_POSITION_UPDATE = "chat.queue_position_update"
    SESSION_ENDED = "chat.session_ended"

    # Agent events
    AGENT_STATUS_CHANGED = "agent.status_changed"
    NEW_CHAT_IN_QUEUE = "agent.new_chat_in_queue"

    # System events
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


@dataclass
class ChatWebSocketMessage:
    """WebSocket message structure for chat."""
    event: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "event": self.event,
            "data": self.data,
            "timestamp": self.timestamp,
        })


@dataclass
class ChatConnection:
    """Represents a WebSocket connection for chat."""
    websocket: WebSocket
    user_id: int
    session_id: Optional[int] = None  # Chat session ID (if in active chat)
    is_agent: bool = False
    agent_member_id: Optional[int] = None  # TeamMember ID for agents
    connected_at: datetime = field(default_factory=datetime.utcnow)


class ChatConnectionManager:
    """
    Manages WebSocket connections for the chat support system.

    Features:
    - Session-based connection tracking (customers and agents in same chat)
    - Agent pool for broadcasting new chat notifications
    - Typing indicators
    - Chat status change notifications
    """

    def __init__(self):
        # Chat session ID -> Set of connections (both customer and agent)
        self.session_connections: Dict[int, Set[ChatConnection]] = {}

        # User ID -> Connection (for customers not yet in active chat)
        self.user_connections: Dict[int, ChatConnection] = {}

        # Agent team member ID -> Connection (for agents)
        self.agent_connections: Dict[int, ChatConnection] = {}

        # Team ID -> Set of agent member IDs (for broadcasting new chats to team)
        self.team_agents: Dict[int, Set[int]] = {}

        # All active connections for management
        self.all_connections: Dict[WebSocket, ChatConnection] = {}

    async def connect_customer(
        self,
        websocket: WebSocket,
        user_id: int,
        session_id: Optional[int] = None,
    ) -> ChatConnection:
        """
        Connect a customer to the chat WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: Customer's user ID
            session_id: Optional chat session ID if already in a chat
        """
        await websocket.accept()

        connection = ChatConnection(
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
            is_agent=False,
        )

        self.all_connections[websocket] = connection
        self.user_connections[user_id] = connection

        if session_id:
            self._add_to_session(connection, session_id)

        logger.info(f"Customer connected: user_id={user_id}, session_id={session_id}")

        # Send connection confirmation
        await self._send_to_connection(
            connection,
            ChatWebSocketMessage(
                event=ChatEventType.CONNECTION_ESTABLISHED,
                data={
                    "user_id": user_id,
                    "session_id": session_id,
                    "role": "customer",
                },
            ),
        )

        return connection

    async def connect_agent(
        self,
        websocket: WebSocket,
        user_id: int,
        agent_member_id: int,
        team_ids: List[int],
    ) -> ChatConnection:
        """
        Connect an agent to the chat WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: Agent's user ID
            agent_member_id: Agent's TeamMember ID
            team_ids: List of team IDs the agent belongs to
        """
        await websocket.accept()

        connection = ChatConnection(
            websocket=websocket,
            user_id=user_id,
            is_agent=True,
            agent_member_id=agent_member_id,
        )

        self.all_connections[websocket] = connection
        self.agent_connections[agent_member_id] = connection

        # Add agent to team groups for broadcasting
        for team_id in team_ids:
            if team_id not in self.team_agents:
                self.team_agents[team_id] = set()
            self.team_agents[team_id].add(agent_member_id)

        logger.info(f"Agent connected: user_id={user_id}, member_id={agent_member_id}, teams={team_ids}")

        # Send connection confirmation
        await self._send_to_connection(
            connection,
            ChatWebSocketMessage(
                event=ChatEventType.CONNECTION_ESTABLISHED,
                data={
                    "user_id": user_id,
                    "agent_member_id": agent_member_id,
                    "role": "agent",
                    "teams": team_ids,
                },
            ),
        )

        return connection

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        """
        connection = self.all_connections.pop(websocket, None)
        if not connection:
            return

        # Remove from user connections
        if not connection.is_agent and connection.user_id in self.user_connections:
            del self.user_connections[connection.user_id]

        # Remove from agent connections
        if connection.is_agent and connection.agent_member_id:
            self.agent_connections.pop(connection.agent_member_id, None)

            # Remove from team groups
            for team_agents in self.team_agents.values():
                team_agents.discard(connection.agent_member_id)

        # Remove from session connections
        if connection.session_id and connection.session_id in self.session_connections:
            self.session_connections[connection.session_id].discard(connection)
            if not self.session_connections[connection.session_id]:
                del self.session_connections[connection.session_id]

        logger.info(
            f"Disconnected: user_id={connection.user_id}, "
            f"is_agent={connection.is_agent}, session_id={connection.session_id}"
        )

    def join_session(self, websocket: WebSocket, session_id: int):
        """Add a connection to a chat session room."""
        connection = self.all_connections.get(websocket)
        if connection:
            connection.session_id = session_id
            self._add_to_session(connection, session_id)
            logger.info(f"User {connection.user_id} joined session {session_id}")

    def leave_session(self, websocket: WebSocket, session_id: int):
        """Remove a connection from a chat session room."""
        connection = self.all_connections.get(websocket)
        if connection:
            connection.session_id = None
            if session_id in self.session_connections:
                self.session_connections[session_id].discard(connection)
                if not self.session_connections[session_id]:
                    del self.session_connections[session_id]
            logger.info(f"User {connection.user_id} left session {session_id}")

    def _add_to_session(self, connection: ChatConnection, session_id: int):
        """Internal: add connection to session room."""
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection)

    async def _send_to_connection(
        self,
        connection: ChatConnection,
        message: ChatWebSocketMessage,
    ):
        """Send message to a specific connection."""
        try:
            await connection.websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def broadcast_to_session(
        self,
        session_id: int,
        message: ChatWebSocketMessage,
        exclude_user_id: Optional[int] = None,
    ):
        """
        Broadcast message to all connections in a chat session.

        Args:
            session_id: Chat session ID
            message: Message to broadcast
            exclude_user_id: Optional user ID to exclude from broadcast
        """
        connections = self.session_connections.get(session_id, set())

        for connection in connections.copy():
            if exclude_user_id and connection.user_id == exclude_user_id:
                continue

            try:
                await connection.websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Failed to broadcast to session {session_id}: {e}")
                self.disconnect(connection.websocket)

    async def send_to_user(self, user_id: int, message: ChatWebSocketMessage):
        """Send message to a specific customer."""
        connection = self.user_connections.get(user_id)
        if connection:
            await self._send_to_connection(connection, message)

    async def send_to_agent(self, agent_member_id: int, message: ChatWebSocketMessage):
        """Send message to a specific agent."""
        connection = self.agent_connections.get(agent_member_id)
        if connection:
            await self._send_to_connection(connection, message)

    async def broadcast_to_team_agents(
        self,
        team_id: Optional[int],
        message: ChatWebSocketMessage,
    ):
        """
        Broadcast message to all online agents in a team.

        Args:
            team_id: Team ID (None for all agents/general queue)
            message: Message to broadcast
        """
        if team_id:
            agent_ids = self.team_agents.get(team_id, set())
        else:
            # Broadcast to all connected agents
            agent_ids = set(self.agent_connections.keys())

        for agent_id in agent_ids.copy():
            connection = self.agent_connections.get(agent_id)
            if connection:
                try:
                    await connection.websocket.send_text(message.to_json())
                except Exception as e:
                    logger.error(f"Failed to broadcast to agent {agent_id}: {e}")
                    self.disconnect(connection.websocket)

    async def broadcast_to_all_agents(self, message: ChatWebSocketMessage):
        """Broadcast message to all connected agents."""
        for agent_id, connection in list(self.agent_connections.items()):
            try:
                await connection.websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Failed to broadcast to agent {agent_id}: {e}")
                self.disconnect(connection.websocket)

    # =========================================================================
    # HELPER METHODS FOR COMMON CHAT EVENTS
    # =========================================================================

    async def notify_new_message(
        self,
        session_id: int,
        message_data: Dict[str, Any],
        sender_user_id: int,
    ):
        """Notify all participants in a session about a new message."""
        await self.broadcast_to_session(
            session_id,
            ChatWebSocketMessage(
                event=ChatEventType.NEW_MESSAGE,
                data=message_data,
            ),
            exclude_user_id=sender_user_id,
        )

    async def notify_typing(
        self,
        session_id: int,
        user_id: int,
        is_typing: bool,
        sender_name: Optional[str] = None,
    ):
        """Notify typing status to other participants."""
        event = ChatEventType.TYPING_START if is_typing else ChatEventType.TYPING_STOP
        await self.broadcast_to_session(
            session_id,
            ChatWebSocketMessage(
                event=event,
                data={
                    "user_id": user_id,
                    "sender_name": sender_name,
                },
            ),
            exclude_user_id=user_id,
        )

    async def notify_agent_joined(
        self,
        session_id: int,
        agent_member_id: int,
        agent_name: str,
        user_id: int,
    ):
        """Notify customer that an agent has joined the chat."""
        # Notify customer
        await self.send_to_user(
            user_id,
            ChatWebSocketMessage(
                event=ChatEventType.AGENT_JOINED,
                data={
                    "session_id": session_id,
                    "agent_member_id": agent_member_id,
                    "agent_name": agent_name,
                },
            ),
        )

    async def notify_agent_left(
        self,
        session_id: int,
        agent_name: str,
        user_id: int,
    ):
        """Notify customer that the agent has left the chat."""
        await self.send_to_user(
            user_id,
            ChatWebSocketMessage(
                event=ChatEventType.AGENT_LEFT,
                data={
                    "session_id": session_id,
                    "agent_name": agent_name,
                },
            ),
        )

    async def notify_session_status_changed(
        self,
        session_id: int,
        new_status: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        """Notify all participants about session status change."""
        data = {
            "session_id": session_id,
            "status": new_status,
            **(additional_data or {}),
        }
        await self.broadcast_to_session(
            session_id,
            ChatWebSocketMessage(
                event=ChatEventType.SESSION_STATUS_CHANGED,
                data=data,
            ),
        )

    async def notify_session_ended(
        self,
        session_id: int,
        ended_by: str,  # "customer", "agent", "system"
        reason: Optional[str] = None,
    ):
        """Notify all participants that the chat session has ended."""
        await self.broadcast_to_session(
            session_id,
            ChatWebSocketMessage(
                event=ChatEventType.SESSION_ENDED,
                data={
                    "session_id": session_id,
                    "ended_by": ended_by,
                    "reason": reason,
                },
            ),
        )

    async def notify_queue_position(
        self,
        user_id: int,
        session_id: int,
        position: int,
    ):
        """Notify customer about their queue position."""
        await self.send_to_user(
            user_id,
            ChatWebSocketMessage(
                event=ChatEventType.QUEUE_POSITION_UPDATE,
                data={
                    "session_id": session_id,
                    "queue_position": position,
                },
            ),
        )

    async def notify_new_chat_in_queue(
        self,
        team_id: Optional[int],
        session_data: Dict[str, Any],
    ):
        """Notify agents about a new chat in their team's queue."""
        await self.broadcast_to_team_agents(
            team_id,
            ChatWebSocketMessage(
                event=ChatEventType.NEW_CHAT_IN_QUEUE,
                data=session_data,
            ),
        )

    # =========================================================================
    # CONNECTION STATS
    # =========================================================================

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        return {
            "total_connections": len(self.all_connections),
            "customer_connections": len(self.user_connections),
            "agent_connections": len(self.agent_connections),
            "active_sessions": len(self.session_connections),
            "teams_with_agents": len([t for t, a in self.team_agents.items() if a]),
        }

    def is_user_online(self, user_id: int) -> bool:
        """Check if a customer is connected."""
        return user_id in self.user_connections

    def is_agent_online(self, agent_member_id: int) -> bool:
        """Check if an agent is connected."""
        return agent_member_id in self.agent_connections


# Global chat connection manager instance
chat_manager = ChatConnectionManager()


async def authenticate_chat_websocket(
    websocket: WebSocket,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate a WebSocket connection using JWT token.

    Token can be passed as:
    - Query parameter: ?token=xxx
    - First message after connection

    Returns dict with user_id and is_staff if authenticated, None otherwise.
    """
    # Try to get token from query params
    token = websocket.query_params.get("token")
    session_id = websocket.query_params.get("session_id")

    if not token:
        # Wait for token in first message
        try:
            data = await websocket.receive_json()
            token = data.get("token")
            session_id = session_id or data.get("session_id")
        except Exception:
            return None

    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return {
            "user_id": int(user_id),
            "session_id": int(session_id) if session_id else None,
        }
    except JWTError:
        return None
