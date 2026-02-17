"""
Admin routes for live chat management.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database import get_db
from auth import get_current_user
from models import (
    User, SupportTeam, TeamMember, ChatSession, ChatMessage,
    AgentStatus, StaffRole
)
from schemas import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionList,
    ChatMessageCreate, ChatMessageResponse,
    AgentStatusUpdate, AgentStatusResponse
)
from services.ticket_service import ChatService
from services.novah_service import novah_service

router = APIRouter(prefix="/admin/chat", tags=["Admin - Chat"])


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def require_staff(user: User):
    """Verify user is a staff member."""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")


def enrich_session_response(db: Session, session: ChatSession) -> ChatSessionResponse:
    """Add related data to session response."""
    user = db.query(User).filter(User.id == session.user_id).first()
    team = db.query(SupportTeam).filter(SupportTeam.id == session.team_id).first() if session.team_id else None

    agent_name = None
    if session.agent_id:
        member = db.query(TeamMember).filter(TeamMember.id == session.agent_id).first()
        if member:
            agent_user = db.query(User).filter(User.id == member.user_id).first()
            agent_name = agent_user.full_name if agent_user else None

    return ChatSessionResponse(
        id=session.id,
        session_token=session.session_token,
        user_id=session.user_id,
        agent_id=session.agent_id,
        team_id=session.team_id,
        status=session.status,
        queue_position=session.queue_position,
        started_at=session.started_at,
        accepted_at=session.accepted_at,
        ended_at=session.ended_at,
        ticket_id=session.ticket_id,
        user_name=user.full_name if user else None,
        agent_name=agent_name,
        team_name=team.name if team else None
    )


# =============================================================================
# CHAT QUEUE MANAGEMENT (Agent view)
# =============================================================================

@router.get("/queue", response_model=ChatSessionList)
async def get_chat_queue(
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get waiting and active chat sessions."""
    require_staff(current_user)

    query = db.query(ChatSession).filter(
        ChatSession.status.in_(["waiting", "active"])
    )

    if team_id:
        query = query.filter(ChatSession.team_id == team_id)

    sessions = query.order_by(ChatSession.started_at).all()

    waiting = sum(1 for s in sessions if s.status == "waiting")
    active = sum(1 for s in sessions if s.status == "active")

    return ChatSessionList(
        sessions=[enrich_session_response(db, s) for s in sessions],
        total=len(sessions),
        waiting=waiting,
        active=active
    )


@router.get("/my-chats", response_model=ChatSessionList)
async def get_my_active_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current agent's active chats."""
    require_staff(current_user)

    # Get agent's team member IDs
    member_ids = db.query(TeamMember.id).filter(
        and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    ).all()
    member_ids = [m[0] for m in member_ids]

    sessions = db.query(ChatSession).filter(
        and_(
            ChatSession.agent_id.in_(member_ids),
            ChatSession.status == "active"
        )
    ).order_by(ChatSession.started_at).all()

    return ChatSessionList(
        sessions=[enrich_session_response(db, s) for s in sessions],
        total=len(sessions),
        waiting=0,
        active=len(sessions)
    )


@router.post("/queue/{session_id}/accept", response_model=ChatSessionResponse)
async def accept_chat(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Accept a chat from the queue."""
    require_staff(current_user)

    # Get agent's team member
    member = db.query(TeamMember).filter(
        and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    ).first()

    if not member:
        raise HTTPException(status_code=400, detail="You must be a team member to accept chats")

    try:
        session = chat_service.accept_chat(session_id, member.id)
        return enrich_session_response(db, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: int,
    create_ticket: bool = False,
    ticket_subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """End a chat session."""
    require_staff(current_user)

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify agent owns this chat
    member_ids = db.query(TeamMember.id).filter(
        and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    ).all()
    member_ids = [m[0] for m in member_ids]

    if session.agent_id not in member_ids and \
       current_user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not your chat session")

    try:
        chat_service.end_chat(
            session_id,
            create_ticket=create_ticket,
            ticket_subject=ticket_subject
        )
        return {"message": "Chat ended successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/transfer")
async def transfer_chat(
    session_id: int,
    target_team_id: Optional[int] = None,
    target_agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfer chat to another team or agent."""
    require_staff(current_user)

    session = db.query(ChatSession).filter(
        and_(ChatSession.id == session_id, ChatSession.status == "active")
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    # Update agent status (decrease chat count)
    if session.agent_id:
        old_agent = db.query(TeamMember).filter(TeamMember.id == session.agent_id).first()
        if old_agent and old_agent.agent_status:
            old_agent.agent_status.current_chats = max(0, old_agent.agent_status.current_chats - 1)

    if target_agent_id:
        new_agent = db.query(TeamMember).filter(
            and_(TeamMember.id == target_agent_id, TeamMember.is_active == True)
        ).first()
        if not new_agent:
            raise HTTPException(status_code=404, detail="Target agent not found")

        session.agent_id = target_agent_id
        if new_agent.team_id:
            session.team_id = new_agent.team_id

        # Update new agent status
        if new_agent.agent_status:
            new_agent.agent_status.current_chats += 1
    elif target_team_id:
        session.team_id = target_team_id
        session.agent_id = None
        session.status = "waiting"
        # Calculate new queue position
        queue_count = db.query(func.count(ChatSession.id)).filter(
            and_(
                ChatSession.status == "waiting",
                ChatSession.team_id == target_team_id
            )
        ).scalar() or 0
        session.queue_position = queue_count + 1

    db.commit()
    return {"message": "Chat transferred successfully"}


# =============================================================================
# CHAT MESSAGES
# =============================================================================

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    session_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for a chat session."""
    require_staff(current_user)

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

    messages.reverse()  # Return in chronological order

    responses = []
    for msg in messages:
        sender_name = None
        if msg.sender_type == "customer":
            user = db.query(User).filter(User.id == session.user_id).first()
            sender_name = user.full_name if user else "Customer"
        elif msg.sender_type == "agent" and session.agent_id:
            member = db.query(TeamMember).filter(TeamMember.id == session.agent_id).first()
            if member:
                agent_user = db.query(User).filter(User.id == member.user_id).first()
                sender_name = agent_user.full_name if agent_user else "Agent"
        else:
            sender_name = msg.sender_type.capitalize()

        responses.append(ChatMessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            sender_type=msg.sender_type,
            message=msg.message,
            message_type=msg.message_type,
            is_read=msg.is_read,
            created_at=msg.created_at,
            sender_name=sender_name
        ))

    return responses


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse, status_code=201)
async def send_chat_message(
    session_id: int,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message in a chat session (agent)."""
    require_staff(current_user)

    session = db.query(ChatSession).filter(
        and_(ChatSession.id == session_id, ChatSession.status == "active")
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Active session not found")

    msg = ChatMessage(
        session_id=session_id,
        sender_id=current_user.id,
        sender_type="agent",
        message=message_data.message,
        message_type=message_data.message_type
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        sender_type=msg.sender_type,
        message=msg.message,
        message_type=msg.message_type,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name=current_user.full_name or "Agent"
    )


# =============================================================================
# AGENT STATUS
# =============================================================================

@router.get("/status", response_model=AgentStatusResponse)
async def get_my_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current agent's status."""
    require_staff(current_user)

    member = db.query(TeamMember).filter(
        and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Not a team member")

    status = db.query(AgentStatus).filter(
        AgentStatus.team_member_id == member.id
    ).first()

    if not status:
        # Create default status
        status = AgentStatus(team_member_id=member.id, status="offline")
        db.add(status)
        db.commit()
        db.refresh(status)

    team = db.query(SupportTeam).filter(SupportTeam.id == member.team_id).first()

    return AgentStatusResponse(
        id=status.id,
        team_member_id=status.team_member_id,
        status=status.status,
        current_chats=status.current_chats,
        max_chats=status.max_chats,
        last_seen=status.last_seen,
        agent_name=current_user.full_name,
        team_name=team.name if team else None
    )


@router.patch("/status", response_model=AgentStatusResponse)
async def update_my_status(
    status_data: AgentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Update current agent's status."""
    require_staff(current_user)

    member = db.query(TeamMember).filter(
        and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Not a team member")

    status = chat_service.update_agent_status(
        team_member_id=member.id,
        status=status_data.status,
        max_chats=status_data.max_chats
    )

    team = db.query(SupportTeam).filter(SupportTeam.id == member.team_id).first()

    return AgentStatusResponse(
        id=status.id,
        team_member_id=status.team_member_id,
        status=status.status,
        current_chats=status.current_chats,
        max_chats=status.max_chats,
        last_seen=status.last_seen,
        agent_name=current_user.full_name,
        team_name=team.name if team else None
    )


@router.get("/agents/online", response_model=List[AgentStatusResponse])
async def get_online_agents(
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of online agents."""
    require_staff(current_user)

    query = db.query(AgentStatus).filter(AgentStatus.status != "offline")

    if team_id:
        query = query.join(TeamMember).filter(TeamMember.team_id == team_id)

    statuses = query.all()

    responses = []
    for status in statuses:
        member = db.query(TeamMember).filter(TeamMember.id == status.team_member_id).first()
        if member:
            user = db.query(User).filter(User.id == member.user_id).first()
            team = db.query(SupportTeam).filter(SupportTeam.id == member.team_id).first()

            responses.append(AgentStatusResponse(
                id=status.id,
                team_member_id=status.team_member_id,
                status=status.status,
                current_chats=status.current_chats,
                max_chats=status.max_chats,
                last_seen=status.last_seen,
                agent_name=user.full_name if user else None,
                team_name=team.name if team else None
            ))

    return responses


# =============================================================================
# CUSTOMER-FACING CHAT ENDPOINTS
# =============================================================================

customer_chat_router = APIRouter(prefix="/chat", tags=["Support Chat"])


@customer_chat_router.post("/start", response_model=ChatSessionResponse)
async def start_chat(
    chat_data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Start a new chat session (customer). Starts with Novah AI."""
    # Check if user already has an active chat
    existing = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if existing:
        return enrich_session_response(db, existing)

    session = chat_service.create_session(
        user_id=current_user.id,
        team_id=chat_data.team_id
    )

    # Start with Novah AI handling
    session.is_ai_handled = True
    session.status = "active"  # AI handles immediately
    db.commit()

    # Send Novah's greeting message
    greeting = novah_service.get_greeting()
    greeting_msg = ChatMessage(
        session_id=session.id,
        sender_id=None,
        sender_type="bot",
        message=greeting,
        message_type="text"
    )
    db.add(greeting_msg)
    db.commit()

    return enrich_session_response(db, session)


@customer_chat_router.get("/session", response_model=Optional[ChatSessionResponse])
async def get_my_chat_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's active chat session."""
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if not session:
        return None

    return enrich_session_response(db, session)


@customer_chat_router.get("/session/messages", response_model=List[ChatMessageResponse])
async def get_my_chat_messages(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages for current user's chat session."""
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active chat session")

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

    messages.reverse()

    responses = []
    for msg in messages:
        if msg.sender_type == "customer":
            sender_name = "You"
        elif msg.sender_type == "agent":
            sender_name = "Support Agent"
        else:
            sender_name = "System"

        responses.append(ChatMessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            sender_type=msg.sender_type,
            message=msg.message,
            message_type=msg.message_type,
            is_read=msg.is_read,
            created_at=msg.created_at,
            sender_name=sender_name
        ))

    return responses


@customer_chat_router.post("/session/messages", response_model=ChatMessageResponse, status_code=201)
async def send_customer_message(
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message in chat (customer). If AI-handled, get Novah response."""
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active chat session")

    # Save customer message
    msg = ChatMessage(
        session_id=session.id,
        sender_id=current_user.id,
        sender_type="customer",
        message=message_data.message,
        message_type=message_data.message_type
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # If chat is AI-handled, generate Novah response
    if session.is_ai_handled:
        # Get conversation history
        history = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at).all()

        # Generate Novah response
        response = novah_service.generate_response(
            message=message_data.message,
            session=session,
            db=db,
            conversation_history=history
        )

        # Check if should transfer to agent
        if response["should_transfer"]:
            # Transfer to human agent
            session.is_ai_handled = False
            session.ai_transferred_at = datetime.utcnow()
            session.ai_resolution_status = "transferred"
            session.status = "waiting"

            # Calculate queue position
            queue_count = db.query(func.count(ChatSession.id)).filter(
                and_(
                    ChatSession.status == "waiting",
                    ChatSession.is_ai_handled == False
                )
            ).scalar() or 0
            session.queue_position = queue_count + 1

            # Send transfer message
            transfer_msg = ChatMessage(
                session_id=session.id,
                sender_id=None,
                sender_type="bot",
                message=novah_service.create_transfer_message(response["transfer_reason"]),
                message_type="text"
            )
            db.add(transfer_msg)
        else:
            # Send Novah's response
            bot_msg = ChatMessage(
                session_id=session.id,
                sender_id=None,
                sender_type="bot",
                message=response["response"],
                message_type="text"
            )
            db.add(bot_msg)

        db.commit()

    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        sender_type=msg.sender_type,
        message=msg.message,
        message_type=msg.message_type,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name="You"
    )


@customer_chat_router.post("/session/transfer-to-agent")
async def request_human_agent(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request transfer from Novah AI to human agent."""
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active chat session")

    if not session.is_ai_handled:
        return {"message": "Already connected to human agent", "status": session.status}

    # Transfer to human agent queue
    session.is_ai_handled = False
    session.ai_transferred_at = datetime.utcnow()
    session.ai_resolution_status = "transferred"
    session.status = "waiting"

    # Calculate queue position
    queue_count = db.query(func.count(ChatSession.id)).filter(
        and_(
            ChatSession.status == "waiting",
            ChatSession.is_ai_handled == False
        )
    ).scalar() or 0
    session.queue_position = queue_count + 1

    # Send system message
    transfer_msg = ChatMessage(
        session_id=session.id,
        sender_id=None,
        sender_type="system",
        message="You've been added to the queue for a human agent. Please wait while we connect you with the next available team member.",
        message_type="text"
    )
    db.add(transfer_msg)
    db.commit()

    return {
        "message": "Transferred to agent queue",
        "queue_position": session.queue_position
    }


@customer_chat_router.post("/session/end")
async def end_my_chat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """End current user's chat session."""
    session = db.query(ChatSession).filter(
        and_(
            ChatSession.user_id == current_user.id,
            ChatSession.status.in_(["waiting", "active"])
        )
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active chat session")

    # Mark AI resolution status if ended during AI handling
    if session.is_ai_handled:
        session.ai_resolution_status = "resolved_by_ai"

    chat_service.end_chat(session.id)

    return {"message": "Chat ended"}
