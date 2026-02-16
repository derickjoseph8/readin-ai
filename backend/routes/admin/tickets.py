"""
Admin routes for ticket management.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from database import get_db
from auth import get_current_user
from models import (
    User, SupportTeam, TeamMember, SupportTicket, TicketMessage,
    SLAConfig, AdminActivityLog, StaffRole
)
from schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetail, TicketList,
    TicketMessageCreate, TicketMessageResponse,
    SLAConfigCreate, SLAConfigUpdate, SLAConfigResponse
)
from services.ticket_service import TicketService

router = APIRouter(prefix="/admin/tickets", tags=["Admin - Tickets"])


def get_ticket_service(db: Session = Depends(get_db)) -> TicketService:
    return TicketService(db)


def require_staff(user: User):
    """Verify user is a staff member."""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")


def require_admin(user: User):
    """Verify user is admin or super_admin."""
    if not user.is_staff or user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")


def get_user_team_ids(db: Session, user: User) -> List[int]:
    """Get list of team IDs the user belongs to."""
    if user.staff_role in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        # Admins can see all teams
        return [t.id for t in db.query(SupportTeam.id).all()]

    members = db.query(TeamMember).filter(
        and_(TeamMember.user_id == user.id, TeamMember.is_active == True)
    ).all()
    return [m.team_id for m in members]


def enrich_ticket_response(db: Session, ticket: SupportTicket) -> TicketResponse:
    """Add related data to ticket response."""
    user = db.query(User).filter(User.id == ticket.user_id).first()
    team = db.query(SupportTeam).filter(SupportTeam.id == ticket.team_id).first() if ticket.team_id else None

    assigned_to_name = None
    if ticket.assigned_to_id:
        member = db.query(TeamMember).filter(TeamMember.id == ticket.assigned_to_id).first()
        if member:
            assigned_user = db.query(User).filter(User.id == member.user_id).first()
            assigned_to_name = assigned_user.full_name if assigned_user else None

    message_count = db.query(func.count(TicketMessage.id)).filter(
        TicketMessage.ticket_id == ticket.id
    ).scalar()

    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        user_id=ticket.user_id,
        team_id=ticket.team_id,
        assigned_to_id=ticket.assigned_to_id,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        subject=ticket.subject,
        description=ticket.description,
        source=ticket.source,
        sla_first_response_due=ticket.sla_first_response_due,
        sla_resolution_due=ticket.sla_resolution_due,
        first_response_at=ticket.first_response_at,
        sla_breached=ticket.sla_breached,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        team_name=team.name if team else None,
        assigned_to_name=assigned_to_name,
        message_count=message_count
    )


# =============================================================================
# TICKET CRUD
# =============================================================================

@router.get("/", response_model=TicketList)
async def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    team_id: Optional[int] = None,
    assigned_to_me: bool = False,
    unassigned: bool = False,
    sla_breached: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List tickets with filters."""
    require_staff(current_user)

    team_ids = get_user_team_ids(db, current_user)
    query = db.query(SupportTicket)

    # Filter by user's teams (unless admin)
    if current_user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        query = query.filter(SupportTicket.team_id.in_(team_ids))

    if status:
        query = query.filter(SupportTicket.status == status)
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    if category:
        query = query.filter(SupportTicket.category == category)
    if team_id:
        query = query.filter(SupportTicket.team_id == team_id)
    if sla_breached is not None:
        query = query.filter(SupportTicket.sla_breached == sla_breached)
    if unassigned:
        query = query.filter(SupportTicket.assigned_to_id.is_(None))
    if assigned_to_me:
        # Get current user's team member IDs
        my_member_ids = db.query(TeamMember.id).filter(
            and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
        ).all()
        my_member_ids = [m[0] for m in my_member_ids]
        query = query.filter(SupportTicket.assigned_to_id.in_(my_member_ids))

    total = query.count()

    # Get status and priority counts
    status_counts = {}
    priority_counts = {}
    for s in ["open", "in_progress", "waiting_customer", "waiting_internal", "resolved", "closed"]:
        status_counts[s] = query.filter(SupportTicket.status == s).count()
    for p in ["urgent", "high", "medium", "low"]:
        priority_counts[p] = query.filter(SupportTicket.priority == p).count()

    tickets = query.order_by(
        SupportTicket.priority.desc(),
        SupportTicket.created_at.desc()
    ).offset(offset).limit(limit).all()

    ticket_responses = [enrich_ticket_response(db, t) for t in tickets]

    return TicketList(
        tickets=ticket_responses,
        total=total,
        by_status=status_counts,
        by_priority=priority_counts
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ticket details with messages."""
    require_staff(current_user)

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check access
    team_ids = get_user_team_ids(db, current_user)
    if current_user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        if ticket.team_id not in team_ids:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get messages
    messages = db.query(TicketMessage).filter(
        TicketMessage.ticket_id == ticket_id
    ).order_by(TicketMessage.created_at).all()

    message_responses = []
    for msg in messages:
        sender_name = None
        if msg.sender_user_id:
            user = db.query(User).filter(User.id == msg.sender_user_id).first()
            sender_name = user.full_name if user else "Customer"
        elif msg.sender_member_id:
            member = db.query(TeamMember).filter(TeamMember.id == msg.sender_member_id).first()
            if member:
                user = db.query(User).filter(User.id == member.user_id).first()
                sender_name = user.full_name if user else "Agent"
        else:
            sender_name = "System"

        message_responses.append(TicketMessageResponse(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_type=msg.sender_type,
            message=msg.message,
            attachments=msg.attachments or [],
            is_internal=msg.is_internal,
            created_at=msg.created_at,
            sender_name=sender_name
        ))

    ticket_response = enrich_ticket_response(db, ticket)

    return TicketDetail(
        **ticket_response.model_dump(),
        messages=message_responses
    )


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    update_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Update ticket details."""
    require_staff(current_user)

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Check access
    team_ids = get_user_team_ids(db, current_user)
    if current_user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        if ticket.team_id not in team_ids:
            raise HTTPException(status_code=403, detail="Access denied")

    # Track changes
    changes = {}

    if update_data.status:
        changes["status"] = {"old": ticket.status, "new": update_data.status}
        ticket_service.update_ticket_status(ticket_id, update_data.status)

    if update_data.priority:
        changes["priority"] = {"old": ticket.priority, "new": update_data.priority}
        ticket.priority = update_data.priority
        # Recalculate SLA
        sla_deadlines = ticket_service.calculate_sla_deadlines(update_data.priority, ticket.created_at)
        ticket.sla_first_response_due = sla_deadlines["first_response_due"]
        ticket.sla_resolution_due = sla_deadlines["resolution_due"]

    if update_data.team_id is not None:
        changes["team_id"] = {"old": ticket.team_id, "new": update_data.team_id}
        ticket.team_id = update_data.team_id
        ticket.assigned_to_id = None  # Reset assignment when changing team

    if update_data.assigned_to_id is not None:
        changes["assigned_to_id"] = {"old": ticket.assigned_to_id, "new": update_data.assigned_to_id}
        ticket.assigned_to_id = update_data.assigned_to_id

    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    # Log activity
    log = AdminActivityLog(
        user_id=current_user.id,
        action="update_ticket",
        entity_type="ticket",
        entity_id=ticket_id,
        details=changes
    )
    db.add(log)
    db.commit()

    return enrich_ticket_response(db, ticket)


@router.post("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    team_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Assign ticket to team/agent."""
    require_staff(current_user)

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_service.assign_ticket(ticket, team_id, agent_id)

    return {"message": "Ticket assigned successfully"}


@router.post("/{ticket_id}/claim")
async def claim_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim ticket for yourself."""
    require_staff(current_user)

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.assigned_to_id:
        raise HTTPException(status_code=400, detail="Ticket is already assigned")

    # Get current user's team member for this team
    member = db.query(TeamMember).filter(
        and_(
            TeamMember.user_id == current_user.id,
            TeamMember.team_id == ticket.team_id,
            TeamMember.is_active == True
        )
    ).first()

    if not member and current_user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="You are not a member of this ticket's team")

    if member:
        ticket.assigned_to_id = member.id
    else:
        # Admin claiming from different team - assign to first available team membership
        any_member = db.query(TeamMember).filter(
            and_(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
        ).first()
        if any_member:
            ticket.assigned_to_id = any_member.id

    ticket.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Ticket claimed successfully"}


# =============================================================================
# TICKET MESSAGES
# =============================================================================

@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=201)
async def add_message(
    ticket_id: int,
    message_data: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Add a reply to a ticket."""
    require_staff(current_user)

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get team member ID
    member = db.query(TeamMember).filter(
        and_(
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True
        )
    ).first()

    msg = ticket_service.add_message(
        ticket_id=ticket_id,
        sender_member_id=member.id if member else None,
        sender_type="agent",
        message=message_data.message,
        is_internal=message_data.is_internal,
        attachments=message_data.attachments
    )

    return TicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_type=msg.sender_type,
        message=msg.message,
        attachments=msg.attachments or [],
        is_internal=msg.is_internal,
        created_at=msg.created_at,
        sender_name=current_user.full_name or current_user.email
    )


# =============================================================================
# SLA CONFIGURATION
# =============================================================================

@router.get("/sla/config", response_model=List[SLAConfigResponse])
async def list_sla_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List SLA configurations."""
    require_admin(current_user)

    configs = db.query(SLAConfig).order_by(SLAConfig.priority).all()
    return [SLAConfigResponse(**c.__dict__) for c in configs]


@router.post("/sla/config", response_model=SLAConfigResponse, status_code=201)
async def create_sla_config(
    config_data: SLAConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create SLA configuration for a priority level."""
    require_admin(current_user)

    existing = db.query(SLAConfig).filter(SLAConfig.priority == config_data.priority).first()
    if existing:
        raise HTTPException(status_code=400, detail="SLA config for this priority already exists")

    config = SLAConfig(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)

    return SLAConfigResponse(**config.__dict__)


@router.patch("/sla/config/{priority}", response_model=SLAConfigResponse)
async def update_sla_config(
    priority: str,
    update_data: SLAConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update SLA configuration."""
    require_admin(current_user)

    config = db.query(SLAConfig).filter(SLAConfig.priority == priority).first()
    if not config:
        raise HTTPException(status_code=404, detail="SLA config not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)

    return SLAConfigResponse(**config.__dict__)


# =============================================================================
# CUSTOMER-FACING TICKET ENDPOINTS (for dashboard)
# =============================================================================

customer_router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


@customer_router.post("/", response_model=TicketResponse, status_code=201)
async def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Create a new support ticket (customer-facing)."""
    ticket = ticket_service.create_ticket(
        user_id=current_user.id,
        category=ticket_data.category,
        subject=ticket_data.subject,
        description=ticket_data.description,
        priority=ticket_data.priority,
        source="dashboard"
    )

    return enrich_ticket_response(db, ticket)


@customer_router.get("/my-tickets", response_model=TicketList)
async def list_my_tickets(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List current user's tickets."""
    query = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id)

    if status:
        query = query.filter(SupportTicket.status == status)

    total = query.count()

    # Status counts
    status_counts = {}
    for s in ["open", "in_progress", "waiting_customer", "waiting_internal", "resolved", "closed"]:
        status_counts[s] = db.query(func.count(SupportTicket.id)).filter(
            and_(SupportTicket.user_id == current_user.id, SupportTicket.status == s)
        ).scalar()

    tickets = query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()

    return TicketList(
        tickets=[enrich_ticket_response(db, t) for t in tickets],
        total=total,
        by_status=status_counts,
        by_priority={}
    )


@customer_router.get("/{ticket_id}", response_model=TicketDetail)
async def get_my_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ticket details (customer view - excludes internal notes)."""
    ticket = db.query(SupportTicket).filter(
        and_(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id)
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get messages (exclude internal)
    messages = db.query(TicketMessage).filter(
        and_(
            TicketMessage.ticket_id == ticket_id,
            TicketMessage.is_internal == False
        )
    ).order_by(TicketMessage.created_at).all()

    message_responses = []
    for msg in messages:
        sender_name = "Support Team" if msg.sender_type == "agent" else "You"
        message_responses.append(TicketMessageResponse(
            id=msg.id,
            ticket_id=msg.ticket_id,
            sender_type=msg.sender_type,
            message=msg.message,
            attachments=msg.attachments or [],
            is_internal=msg.is_internal,
            created_at=msg.created_at,
            sender_name=sender_name
        ))

    ticket_response = enrich_ticket_response(db, ticket)

    return TicketDetail(
        **ticket_response.model_dump(),
        messages=message_responses
    )


@customer_router.post("/{ticket_id}/reply", response_model=TicketMessageResponse, status_code=201)
async def reply_to_ticket(
    ticket_id: int,
    message_data: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service)
):
    """Reply to a ticket (customer)."""
    ticket = db.query(SupportTicket).filter(
        and_(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id)
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == "closed":
        raise HTTPException(status_code=400, detail="Cannot reply to a closed ticket")

    msg = ticket_service.add_message(
        ticket_id=ticket_id,
        sender_user_id=current_user.id,
        sender_type="customer",
        message=message_data.message,
        attachments=message_data.attachments
    )

    return TicketMessageResponse(
        id=msg.id,
        ticket_id=msg.ticket_id,
        sender_type=msg.sender_type,
        message=msg.message,
        attachments=msg.attachments or [],
        is_internal=False,
        created_at=msg.created_at,
        sender_name=current_user.full_name or "You"
    )
