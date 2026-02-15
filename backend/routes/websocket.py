"""WebSocket routes for real-time updates."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.websocket_manager import (
    manager,
    authenticate_websocket,
    WebSocketMessage,
    EventType,
)

logger = logging.getLogger("websocket")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates.

    Authentication:
    - Pass JWT token as query param: /ws?token=xxx
    - Or send as first message: {"token": "xxx"}

    Message format (JSON):
    - Outgoing: {"event": "event.type", "data": {...}, "timestamp": "ISO-8601"}
    - Incoming: {"action": "action.type", "data": {...}}

    Supported incoming actions:
    - ping: Heartbeat check
    - subscribe: Subscribe to a room/channel
    - unsubscribe: Unsubscribe from a room/channel
    """
    # Authenticate
    user_id = await authenticate_websocket(websocket)

    if not user_id:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Connect
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive and handle messages
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "ping":
                # Heartbeat
                await manager.send_personal_message(
                    WebSocketMessage(event=EventType.PONG, data={}),
                    websocket,
                )

            elif action == "subscribe":
                # Subscribe to a room
                room = data.get("room")
                if room:
                    manager.join_room(user_id, room)
                    await manager.send_personal_message(
                        WebSocketMessage(
                            event="subscribed",
                            data={"room": room},
                        ),
                        websocket,
                    )

            elif action == "unsubscribe":
                # Unsubscribe from a room
                room = data.get("room")
                if room:
                    manager.leave_room(user_id, room)
                    await manager.send_personal_message(
                        WebSocketMessage(
                            event="unsubscribed",
                            data={"room": room},
                        ),
                        websocket,
                    )

            else:
                # Unknown action
                await manager.send_personal_message(
                    WebSocketMessage(
                        event=EventType.ERROR,
                        data={"message": f"Unknown action: {action}"},
                    ),
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/ws/status")
def websocket_status():
    """
    Get WebSocket server status.

    Returns connection statistics.
    """
    return {
        "connected_users": manager.get_user_count(),
        "total_connections": manager.get_connection_count(),
        "rooms": list(manager.rooms.keys()),
    }
