"""
Ticket routing and SLA management service for support tickets.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models import (
    SupportTeam, TeamMember, SupportTicket, TicketMessage,
    SLAConfig, AgentStatus, ChatSession, User, CATEGORY_TEAM_MAP
)


class TicketService:
    """Service for ticket routing, assignment, and SLA tracking."""

    def __init__(self, db: Session):
        self.db = db

    def generate_ticket_number(self) -> str:
        """Generate unique ticket number: TKT-YYYY-XXXXX"""
        year = datetime.utcnow().year

        # Get the count of tickets this year
        count = self.db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.ticket_number.like(f"TKT-{year}-%")
        ).scalar() or 0

        return f"TKT-{year}-{str(count + 1).zfill(5)}"

    def get_team_for_category(self, category: str) -> Optional[SupportTeam]:
        """Get the appropriate team for a ticket category."""
        team_slug = CATEGORY_TEAM_MAP.get(category.lower(), "tech-support")

        team = self.db.query(SupportTeam).filter(
            and_(
                SupportTeam.slug == team_slug,
                SupportTeam.is_active == True,
                SupportTeam.accepts_tickets == True
            )
        ).first()

        return team

    def get_sla_config(self, priority: str) -> Optional[SLAConfig]:
        """Get SLA configuration for a priority level."""
        return self.db.query(SLAConfig).filter(
            and_(
                SLAConfig.priority == priority,
                SLAConfig.is_active == True
            )
        ).first()

    def calculate_sla_deadlines(
        self,
        priority: str,
        created_at: Optional[datetime] = None
    ) -> Dict[str, Optional[datetime]]:
        """Calculate SLA deadlines for a ticket."""
        sla = self.get_sla_config(priority)
        created = created_at or datetime.utcnow()

        if not sla:
            return {
                "first_response_due": None,
                "resolution_due": None
            }

        # Calculate business hours (simplified - 24/7 for now)
        # TODO: Implement business hours calculation
        return {
            "first_response_due": created + timedelta(minutes=sla.first_response_minutes),
            "resolution_due": created + timedelta(minutes=sla.resolution_minutes)
        }

    def find_available_agent(self, team_id: int) -> Optional[TeamMember]:
        """Find an available agent from a team for ticket assignment."""
        # Get online agents with capacity
        available_agents = self.db.query(TeamMember).join(
            AgentStatus, TeamMember.id == AgentStatus.team_member_id
        ).filter(
            and_(
                TeamMember.team_id == team_id,
                TeamMember.is_active == True,
                AgentStatus.status == "online",
                AgentStatus.current_chats < AgentStatus.max_chats
            )
        ).order_by(
            AgentStatus.current_chats  # Assign to agent with least chats
        ).first()

        return available_agents

    def assign_ticket(
        self,
        ticket: SupportTicket,
        team_id: Optional[int] = None,
        agent_id: Optional[int] = None
    ) -> SupportTicket:
        """Assign ticket to a team and optionally an agent."""
        if team_id:
            ticket.team_id = team_id
        elif not ticket.team_id:
            # Auto-assign to appropriate team
            team = self.get_team_for_category(ticket.category)
            if team:
                ticket.team_id = team.id

        if agent_id:
            # Verify agent belongs to the team
            agent = self.db.query(TeamMember).filter(
                and_(
                    TeamMember.id == agent_id,
                    TeamMember.team_id == ticket.team_id,
                    TeamMember.is_active == True
                )
            ).first()
            if agent:
                ticket.assigned_to_id = agent_id
        elif ticket.team_id:
            # Try to auto-assign to available agent
            agent = self.find_available_agent(ticket.team_id)
            if agent:
                ticket.assigned_to_id = agent.id

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def create_ticket(
        self,
        user_id: int,
        category: str,
        subject: str,
        description: str,
        priority: str = "medium",
        source: str = "dashboard"
    ) -> SupportTicket:
        """Create a new support ticket with auto-routing."""
        ticket_number = self.generate_ticket_number()
        sla_deadlines = self.calculate_sla_deadlines(priority)

        ticket = SupportTicket(
            ticket_number=ticket_number,
            user_id=user_id,
            category=category,
            priority=priority,
            subject=subject,
            description=description,
            source=source,
            sla_first_response_due=sla_deadlines["first_response_due"],
            sla_resolution_due=sla_deadlines["resolution_due"]
        )

        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        # Auto-assign to team
        self.assign_ticket(ticket)

        return ticket

    def add_message(
        self,
        ticket_id: int,
        sender_user_id: Optional[int] = None,
        sender_member_id: Optional[int] = None,
        sender_type: str = "customer",
        message: str = "",
        is_internal: bool = False,
        attachments: Optional[List[str]] = None
    ) -> TicketMessage:
        """Add a message to a ticket."""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()

        if not ticket:
            raise ValueError("Ticket not found")

        # Record first response time
        if sender_type == "agent" and not ticket.first_response_at:
            ticket.first_response_at = datetime.utcnow()

            # Check for SLA breach
            if ticket.sla_first_response_due and datetime.utcnow() > ticket.sla_first_response_due:
                ticket.sla_breached = True

        # Update ticket status based on response
        if sender_type == "agent" and ticket.status == "open":
            ticket.status = "in_progress"
        elif sender_type == "customer" and ticket.status == "waiting_customer":
            ticket.status = "in_progress"

        msg = TicketMessage(
            ticket_id=ticket_id,
            sender_user_id=sender_user_id,
            sender_member_id=sender_member_id,
            sender_type=sender_type,
            message=message,
            is_internal=is_internal,
            attachments=attachments or []
        )

        self.db.add(msg)
        ticket.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(msg)

        return msg

    def update_ticket_status(
        self,
        ticket_id: int,
        status: str,
        resolved_by_id: Optional[int] = None
    ) -> SupportTicket:
        """Update ticket status."""
        ticket = self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()

        if not ticket:
            raise ValueError("Ticket not found")

        ticket.status = status
        ticket.updated_at = datetime.utcnow()

        if status == "resolved":
            ticket.resolved_at = datetime.utcnow()
            # Check resolution SLA
            if ticket.sla_resolution_due and datetime.utcnow() > ticket.sla_resolution_due:
                ticket.sla_breached = True
        elif status == "closed":
            ticket.closed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get_sla_metrics(self, team_id: Optional[int] = None) -> Dict[str, Any]:
        """Get SLA metrics for dashboard."""
        query = self.db.query(SupportTicket)

        if team_id:
            query = query.filter(SupportTicket.team_id == team_id)

        # Tickets created in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_tickets = query.filter(
            SupportTicket.created_at >= thirty_days_ago
        )

        total = recent_tickets.count()
        breached = recent_tickets.filter(SupportTicket.sla_breached == True).count()

        # Average first response time (in minutes)
        responded_tickets = recent_tickets.filter(
            SupportTicket.first_response_at.isnot(None)
        ).all()

        if responded_tickets:
            avg_response = sum(
                (t.first_response_at - t.created_at).total_seconds() / 60
                for t in responded_tickets
            ) / len(responded_tickets)
        else:
            avg_response = 0

        return {
            "total_tickets": total,
            "sla_breached": breached,
            "sla_breach_rate": (breached / total * 100) if total > 0 else 0,
            "avg_first_response_minutes": round(avg_response, 1)
        }

    def check_and_escalate(self) -> List[SupportTicket]:
        """Check for tickets that need escalation based on SLA."""
        now = datetime.utcnow()

        # Find tickets approaching SLA breach
        tickets_to_escalate = self.db.query(SupportTicket).filter(
            and_(
                SupportTicket.status.in_(["open", "in_progress"]),
                SupportTicket.sla_breached == False,
                or_(
                    SupportTicket.sla_first_response_due <= now,
                    SupportTicket.sla_resolution_due <= now
                )
            )
        ).all()

        for ticket in tickets_to_escalate:
            ticket.sla_breached = True
            # Add system message about escalation
            self.add_message(
                ticket_id=ticket.id,
                sender_type="system",
                message="This ticket has breached SLA and has been escalated.",
                is_internal=True
            )

        self.db.commit()
        return tickets_to_escalate


class ChatService:
    """Service for live chat management."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        user_id: int,
        team_id: Optional[int] = None
    ) -> ChatSession:
        """Create a new chat session."""
        import secrets

        session_token = secrets.token_urlsafe(32)

        # Calculate queue position
        waiting_count = self.db.query(func.count(ChatSession.id)).filter(
            and_(
                ChatSession.status == "waiting",
                ChatSession.team_id == team_id if team_id else True
            )
        ).scalar() or 0

        session = ChatSession(
            session_token=session_token,
            user_id=user_id,
            team_id=team_id,
            status="waiting",
            queue_position=waiting_count + 1
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # Try to auto-assign an agent
        self.try_assign_agent(session)

        return session

    def try_assign_agent(self, session: ChatSession) -> bool:
        """Try to assign an available agent to the chat."""
        if session.agent_id:
            return True

        # Find available agent
        query = self.db.query(TeamMember).join(
            AgentStatus, TeamMember.id == AgentStatus.team_member_id
        ).filter(
            and_(
                TeamMember.is_active == True,
                AgentStatus.status == "online",
                AgentStatus.current_chats < AgentStatus.max_chats
            )
        )

        if session.team_id:
            query = query.filter(TeamMember.team_id == session.team_id)

        agent = query.order_by(AgentStatus.current_chats).first()

        if agent:
            session.agent_id = agent.id
            session.status = "active"
            session.accepted_at = datetime.utcnow()
            session.queue_position = None

            # Update agent's chat count
            agent.agent_status.current_chats += 1

            self.db.commit()
            return True

        return False

    def accept_chat(self, session_id: int, agent_member_id: int) -> ChatSession:
        """Agent accepts a chat from the queue."""
        session = self.db.query(ChatSession).filter(
            and_(
                ChatSession.id == session_id,
                ChatSession.status == "waiting"
            )
        ).first()

        if not session:
            raise ValueError("Chat session not found or already assigned")

        agent = self.db.query(TeamMember).filter(
            and_(
                TeamMember.id == agent_member_id,
                TeamMember.is_active == True
            )
        ).first()

        if not agent:
            raise ValueError("Agent not found")

        session.agent_id = agent_member_id
        session.status = "active"
        session.accepted_at = datetime.utcnow()
        session.queue_position = None

        # Update agent status
        if agent.agent_status:
            agent.agent_status.current_chats += 1

        # Update queue positions for other waiting sessions
        self.db.query(ChatSession).filter(
            and_(
                ChatSession.status == "waiting",
                ChatSession.queue_position > 0
            )
        ).update({
            ChatSession.queue_position: ChatSession.queue_position - 1
        })

        self.db.commit()
        self.db.refresh(session)
        return session

    def end_chat(
        self,
        session_id: int,
        create_ticket: bool = False,
        ticket_subject: Optional[str] = None
    ) -> ChatSession:
        """End a chat session, optionally creating a ticket."""
        session = self.db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()

        if not session:
            raise ValueError("Chat session not found")

        session.status = "ended"
        session.ended_at = datetime.utcnow()

        # Update agent's chat count
        if session.agent_id:
            agent = self.db.query(TeamMember).filter(
                TeamMember.id == session.agent_id
            ).first()
            if agent and agent.agent_status:
                agent.agent_status.current_chats = max(0, agent.agent_status.current_chats - 1)

        # Create ticket from chat if requested
        if create_ticket and ticket_subject:
            ticket_service = TicketService(self.db)

            # Get chat messages for description
            messages = self.db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first().messages

            description = "\n\n".join([
                f"[{m.sender_type}]: {m.message}"
                for m in messages[:10]  # First 10 messages
            ])

            ticket = ticket_service.create_ticket(
                user_id=session.user_id,
                category="general",
                subject=ticket_subject,
                description=f"Created from chat session.\n\n{description}",
                source="chat"
            )

            session.ticket_id = ticket.id

        self.db.commit()
        self.db.refresh(session)
        return session

    def update_agent_status(
        self,
        team_member_id: int,
        status: str,
        max_chats: Optional[int] = None
    ) -> AgentStatus:
        """Update agent availability status."""
        agent_status = self.db.query(AgentStatus).filter(
            AgentStatus.team_member_id == team_member_id
        ).first()

        if not agent_status:
            agent_status = AgentStatus(
                team_member_id=team_member_id,
                status=status,
                max_chats=max_chats or 3
            )
            self.db.add(agent_status)
        else:
            old_status = agent_status.status
            agent_status.status = status

            if max_chats is not None:
                agent_status.max_chats = max_chats

            agent_status.last_seen = datetime.utcnow()

            if status == "online" and old_status == "offline":
                agent_status.went_online_at = datetime.utcnow()
            elif status == "offline" and old_status != "offline":
                agent_status.went_offline_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(agent_status)
        return agent_status

    def get_queue_stats(self, team_id: Optional[int] = None) -> Dict[str, Any]:
        """Get chat queue statistics."""
        query = self.db.query(ChatSession)

        if team_id:
            query = query.filter(ChatSession.team_id == team_id)

        waiting = query.filter(ChatSession.status == "waiting").count()
        active = query.filter(ChatSession.status == "active").count()

        # Get online agents
        agent_query = self.db.query(AgentStatus).filter(
            AgentStatus.status == "online"
        )

        if team_id:
            agent_query = agent_query.join(TeamMember).filter(
                TeamMember.team_id == team_id
            )

        online_agents = agent_query.count()

        return {
            "waiting_chats": waiting,
            "active_chats": active,
            "online_agents": online_agents
        }
