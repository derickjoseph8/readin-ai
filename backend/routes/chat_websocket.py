"""
WebSocket routes for real-time chat support.

Provides WebSocket endpoints for:
- Customer chat connections
- Agent chat connections
- Real-time messaging, typing indicators, and status updates
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from models import User, TeamMember, ChatSession, ChatMessage, SupportTeam
from services.chat_websocket_manager import (
    chat_manager,
    authenticate_chat_websocket,
    ChatWebSocketMessage,
    ChatEventType,
)

logger = logging.getLogger("chat_websocket")

router = APIRouter(tags=["Chat WebSocket"])


@router.websocket("/ws/chat")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    session_id: Optional[int] = Query(None),
):
    """
    Main WebSocket endpoint for customer chat.

    Authentication:
    - Pass JWT token as query param: /ws/chat?token=xxx
    - Optionally pass session_id to join existing chat: /ws/chat?token=xxx&session_id=123

    Message format (JSON):
    - Outgoing: {"event": "event.type", "data": {...}, "timestamp": "ISO-8601"}
    - Incoming: {"action": "action.type", "data": {...}}

    Supported incoming actions:
    - ping: Heartbeat check
    - send_message: Send a chat message
    - typing_start: Indicate user started typing
    - typing_stop: Indicate user stopped typing
    - join_session: Join a chat session
    - leave_session: Leave a chat session
    """
    # Get database session
    from database import SessionLocal
    db = SessionLocal()

    try:
        # Authenticate
        auth_result = await authenticate_chat_websocket(websocket)

        if not auth_result:
            await websocket.close(code=4001, reason="Authentication required")
            return

        user_id = auth_result["user_id"]
        initial_session_id = auth_result.get("session_id") or session_id

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4001, reason="User not found")
            return

        # Verify session if provided
        if initial_session_id:
            session = db.query(ChatSession).filter(
                and_(
                    ChatSession.id == initial_session_id,
                    ChatSession.user_id == user_id,
                    ChatSession.status.in_(["waiting", "active"])
                )
            ).first()
            if not session:
                initial_session_id = None

        # Connect customer
        connection = await chat_manager.connect_customer(
            websocket, user_id, initial_session_id
        )

        try:
            while True:
                # Receive and handle messages
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "ping":
                    # Heartbeat
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event=ChatEventType.PONG,
                            data={}
                        ).to_json()
                    )

                elif action == "send_message":
                    # Send a message in the chat
                    message_text = data.get("message", "").strip()
                    message_type = data.get("message_type", "text")
                    target_session_id = data.get("session_id") or connection.session_id

                    if not target_session_id or not message_text:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "session_id and message are required"}
                            ).to_json()
                        )
                        continue

                    # Verify user is part of this session
                    session = db.query(ChatSession).filter(
                        and_(
                            ChatSession.id == target_session_id,
                            ChatSession.user_id == user_id,
                            ChatSession.status.in_(["waiting", "active"])
                        )
                    ).first()

                    if not session:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "Invalid or inactive session"}
                            ).to_json()
                        )
                        continue

                    # Save message to database
                    msg = ChatMessage(
                        session_id=target_session_id,
                        sender_id=user_id,
                        sender_type="customer",
                        message=message_text,
                        message_type=message_type,
                    )
                    db.add(msg)
                    db.commit()
                    db.refresh(msg)

                    # Broadcast to session participants
                    message_data = {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "sender_type": msg.sender_type,
                        "sender_id": msg.sender_id,
                        "sender_name": user.full_name or "Customer",
                        "message": msg.message,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat(),
                    }

                    await chat_manager.notify_new_message(
                        target_session_id, message_data, user_id
                    )

                    # Send confirmation to sender
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event="chat.message_sent",
                            data=message_data
                        ).to_json()
                    )

                elif action == "typing_start":
                    target_session_id = data.get("session_id") or connection.session_id
                    if target_session_id:
                        await chat_manager.notify_typing(
                            target_session_id, user_id, True, user.full_name
                        )

                elif action == "typing_stop":
                    target_session_id = data.get("session_id") or connection.session_id
                    if target_session_id:
                        await chat_manager.notify_typing(
                            target_session_id, user_id, False, user.full_name
                        )

                elif action == "join_session":
                    new_session_id = data.get("session_id")
                    if new_session_id:
                        # Verify user owns this session
                        session = db.query(ChatSession).filter(
                            and_(
                                ChatSession.id == new_session_id,
                                ChatSession.user_id == user_id,
                                ChatSession.status.in_(["waiting", "active"])
                            )
                        ).first()
                        if session:
                            chat_manager.join_session(websocket, new_session_id)
                            await websocket.send_text(
                                ChatWebSocketMessage(
                                    event="chat.session_joined",
                                    data={"session_id": new_session_id}
                                ).to_json()
                            )

                elif action == "leave_session":
                    leave_session_id = data.get("session_id") or connection.session_id
                    if leave_session_id:
                        chat_manager.leave_session(websocket, leave_session_id)
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event="chat.session_left",
                                data={"session_id": leave_session_id}
                            ).to_json()
                        )

                else:
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event=ChatEventType.ERROR,
                            data={"message": f"Unknown action: {action}"}
                        ).to_json()
                    )

        except WebSocketDisconnect:
            chat_manager.disconnect(websocket)
            logger.info(f"Customer WebSocket disconnected: user={user_id}")
        except Exception as e:
            logger.error(f"Customer WebSocket error: {e}")
            chat_manager.disconnect(websocket)

    finally:
        db.close()


@router.websocket("/ws/chat/agent")
async def agent_chat_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for agent/staff chat connections.

    Authentication:
    - Pass JWT token as query param: /ws/chat/agent?token=xxx
    - Only staff members can connect

    Message format (JSON):
    - Outgoing: {"event": "event.type", "data": {...}, "timestamp": "ISO-8601"}
    - Incoming: {"action": "action.type", "data": {...}}

    Supported incoming actions:
    - ping: Heartbeat check
    - send_message: Send a chat message
    - typing_start: Indicate agent started typing
    - typing_stop: Indicate agent stopped typing
    - join_session: Join/accept a chat session
    - leave_session: Leave a chat session
    - accept_chat: Accept a chat from queue
    """
    from database import SessionLocal
    db = SessionLocal()

    try:
        # Authenticate
        auth_result = await authenticate_chat_websocket(websocket)

        if not auth_result:
            await websocket.close(code=4001, reason="Authentication required")
            return

        user_id = auth_result["user_id"]

        # Get user and verify staff status
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_staff:
            await websocket.close(code=4003, reason="Staff access required")
            return

        # Get agent's team memberships
        team_members = db.query(TeamMember).filter(
            and_(
                TeamMember.user_id == user_id,
                TeamMember.is_active == True
            )
        ).all()

        if not team_members:
            await websocket.close(code=4003, reason="No team membership found")
            return

        # Use the first active team member record
        agent_member = team_members[0]
        team_ids = [tm.team_id for tm in team_members if tm.team_id]

        # Connect agent
        connection = await chat_manager.connect_agent(
            websocket, user_id, agent_member.id, team_ids
        )

        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")

                if action == "ping":
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event=ChatEventType.PONG,
                            data={}
                        ).to_json()
                    )

                elif action == "send_message":
                    message_text = data.get("message", "").strip()
                    message_type = data.get("message_type", "text")
                    target_session_id = data.get("session_id")

                    if not target_session_id or not message_text:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "session_id and message are required"}
                            ).to_json()
                        )
                        continue

                    # Verify agent has access to this session
                    session = db.query(ChatSession).filter(
                        and_(
                            ChatSession.id == target_session_id,
                            ChatSession.status == "active"
                        )
                    ).first()

                    if not session:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "Session not found or not active"}
                            ).to_json()
                        )
                        continue

                    # Verify agent is assigned or is admin
                    member_ids = [tm.id for tm in team_members]
                    if session.agent_id not in member_ids:
                        # Check if user is admin/super_admin
                        from models import StaffRole
                        if user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
                            await websocket.send_text(
                                ChatWebSocketMessage(
                                    event=ChatEventType.ERROR,
                                    data={"message": "Not authorized for this session"}
                                ).to_json()
                            )
                            continue

                    # Save message to database
                    msg = ChatMessage(
                        session_id=target_session_id,
                        sender_id=user_id,
                        sender_type="agent",
                        message=message_text,
                        message_type=message_type,
                    )
                    db.add(msg)
                    db.commit()
                    db.refresh(msg)

                    # Broadcast to session participants
                    message_data = {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "sender_type": msg.sender_type,
                        "sender_id": msg.sender_id,
                        "sender_name": user.full_name or "Support Agent",
                        "message": msg.message,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat(),
                    }

                    await chat_manager.notify_new_message(
                        target_session_id, message_data, user_id
                    )

                    # Send confirmation to sender
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event="chat.message_sent",
                            data=message_data
                        ).to_json()
                    )

                elif action == "typing_start":
                    target_session_id = data.get("session_id")
                    if target_session_id:
                        await chat_manager.notify_typing(
                            target_session_id, user_id, True, user.full_name
                        )

                elif action == "typing_stop":
                    target_session_id = data.get("session_id")
                    if target_session_id:
                        await chat_manager.notify_typing(
                            target_session_id, user_id, False, user.full_name
                        )

                elif action == "join_session":
                    target_session_id = data.get("session_id")
                    if target_session_id:
                        chat_manager.join_session(websocket, target_session_id)
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event="chat.session_joined",
                                data={"session_id": target_session_id}
                            ).to_json()
                        )

                elif action == "leave_session":
                    target_session_id = data.get("session_id")
                    if target_session_id:
                        chat_manager.leave_session(websocket, target_session_id)
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event="chat.session_left",
                                data={"session_id": target_session_id}
                            ).to_json()
                        )

                elif action == "accept_chat":
                    # Accept a chat from the queue
                    target_session_id = data.get("session_id")
                    if not target_session_id:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "session_id is required"}
                            ).to_json()
                        )
                        continue

                    # Get the session
                    session = db.query(ChatSession).filter(
                        and_(
                            ChatSession.id == target_session_id,
                            ChatSession.status == "waiting"
                        )
                    ).first()

                    if not session:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": "Session not found or already assigned"}
                            ).to_json()
                        )
                        continue

                    # Accept the chat
                    from services.ticket_service import ChatService
                    chat_service = ChatService(db)
                    try:
                        session = chat_service.accept_chat(target_session_id, agent_member.id)

                        # Join the session room
                        chat_manager.join_session(websocket, target_session_id)

                        # Notify the customer
                        await chat_manager.notify_agent_joined(
                            target_session_id,
                            agent_member.id,
                            user.full_name or "Support Agent",
                            session.user_id,
                        )

                        # Notify status change
                        await chat_manager.notify_session_status_changed(
                            target_session_id,
                            "active",
                            {"agent_name": user.full_name or "Support Agent"}
                        )

                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event="chat.chat_accepted",
                                data={
                                    "session_id": target_session_id,
                                    "status": "active"
                                }
                            ).to_json()
                        )

                    except ValueError as e:
                        await websocket.send_text(
                            ChatWebSocketMessage(
                                event=ChatEventType.ERROR,
                                data={"message": str(e)}
                            ).to_json()
                        )

                else:
                    await websocket.send_text(
                        ChatWebSocketMessage(
                            event=ChatEventType.ERROR,
                            data={"message": f"Unknown action: {action}"}
                        ).to_json()
                    )

        except WebSocketDisconnect:
            chat_manager.disconnect(websocket)
            logger.info(f"Agent WebSocket disconnected: user={user_id}")
        except Exception as e:
            logger.error(f"Agent WebSocket error: {e}")
            chat_manager.disconnect(websocket)

    finally:
        db.close()


@router.get("/ws/chat/status")
def chat_websocket_status():
    """
    Get chat WebSocket server status.

    Returns connection statistics.
    """
    return chat_manager.get_connection_stats()
