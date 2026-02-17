"""
Admin dashboard routes for analytics and overview.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, cast, Date

from database import get_db
from auth import get_current_user
from models import (
    User, SupportTeam, TeamMember, SupportTicket, ChatSession,
    AgentStatus, AdminActivityLog, StaffRole, Organization
)
from schemas import (
    AdminDashboardStats, AdminTrends, TicketTrend, SubscriptionTrend,
    AdminActivityLogResponse
)
from services.ticket_service import TicketService

router = APIRouter(prefix="/admin/dashboard", tags=["Admin - Dashboard"])


def require_staff(user: User):
    """Verify user is a staff member."""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")


def require_admin(user: User):
    """Verify user is admin or super_admin."""
    if not user.is_staff or user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")


# =============================================================================
# DASHBOARD STATS
# =============================================================================

@router.get("/stats", response_model=AdminDashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get admin dashboard statistics."""
    require_admin(current_user)

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # User stats
    total_users = db.query(func.count(User.id)).filter(User.is_staff == False).scalar()
    trial_users = db.query(func.count(User.id)).filter(
        and_(User.is_staff == False, User.subscription_status == "trial")
    ).scalar()
    paying_users = db.query(func.count(User.id)).filter(
        and_(User.is_staff == False, User.subscription_status == "active")
    ).scalar()

    # Active users (logged in within last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    active_users = db.query(func.count(User.id)).filter(
        and_(
            User.is_staff == False,
            User.last_login >= thirty_days_ago
        )
    ).scalar()

    # New users
    new_today = db.query(func.count(User.id)).filter(
        and_(User.is_staff == False, User.created_at >= today_start)
    ).scalar()
    new_this_week = db.query(func.count(User.id)).filter(
        and_(User.is_staff == False, User.created_at >= week_start)
    ).scalar()
    new_this_month = db.query(func.count(User.id)).filter(
        and_(User.is_staff == False, User.created_at >= month_start)
    ).scalar()

    # Subscription/Revenue stats (simplified - would integrate with Stripe in production)
    # These would typically come from Stripe API
    total_revenue_this_month = paying_users * 9.99  # Simplified calculation
    mrr = paying_users * 9.99
    churn_rate = 0.0  # Would calculate from actual cancellation data

    # Support stats
    ticket_service = TicketService(db)
    sla_metrics = ticket_service.get_sla_metrics()

    open_tickets = db.query(func.count(SupportTicket.id)).filter(
        SupportTicket.status.in_(["open", "in_progress", "waiting_customer", "waiting_internal"])
    ).scalar()

    tickets_today = db.query(func.count(SupportTicket.id)).filter(
        SupportTicket.created_at >= today_start
    ).scalar()

    # Chat stats
    active_chats = db.query(func.count(ChatSession.id)).filter(
        ChatSession.status == "active"
    ).scalar()

    waiting_chats = db.query(func.count(ChatSession.id)).filter(
        ChatSession.status == "waiting"
    ).scalar()

    # Team stats
    total_teams = db.query(func.count(SupportTeam.id)).filter(
        SupportTeam.is_active == True
    ).scalar()

    online_agents = db.query(func.count(AgentStatus.id)).filter(
        AgentStatus.status == "online"
    ).scalar()

    total_agents = db.query(func.count(TeamMember.id)).filter(
        TeamMember.is_active == True
    ).scalar()

    return AdminDashboardStats(
        total_users=total_users,
        active_users=active_users,
        trial_users=trial_users,
        paying_users=paying_users,
        new_users_today=new_today,
        new_users_this_week=new_this_week,
        new_users_this_month=new_this_month,
        total_revenue_this_month=total_revenue_this_month,
        mrr=mrr,
        churn_rate=churn_rate,
        open_tickets=open_tickets,
        tickets_today=tickets_today,
        avg_response_time_minutes=sla_metrics["avg_first_response_minutes"],
        sla_breach_rate=sla_metrics["sla_breach_rate"],
        active_chats=active_chats,
        waiting_chats=waiting_chats,
        total_teams=total_teams,
        online_agents=online_agents,
        total_agents=total_agents
    )


@router.get("/trends", response_model=AdminTrends)
async def get_dashboard_trends(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trend data for charts."""
    require_admin(current_user)

    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Generate date range
    if period == "daily":
        date_format = "%Y-%m-%d"
        date_delta = timedelta(days=1)
    elif period == "weekly":
        date_format = "%Y-W%W"
        date_delta = timedelta(weeks=1)
    else:  # monthly
        date_format = "%Y-%m"
        date_delta = timedelta(days=30)

    # Ticket trends
    ticket_trends = []
    current_date = start_date
    while current_date <= now:
        next_date = current_date + date_delta

        created = db.query(func.count(SupportTicket.id)).filter(
            and_(
                SupportTicket.created_at >= current_date,
                SupportTicket.created_at < next_date
            )
        ).scalar()

        resolved = db.query(func.count(SupportTicket.id)).filter(
            and_(
                SupportTicket.resolved_at >= current_date,
                SupportTicket.resolved_at < next_date
            )
        ).scalar()

        # Average response time for this period
        period_tickets = db.query(SupportTicket).filter(
            and_(
                SupportTicket.created_at >= current_date,
                SupportTicket.created_at < next_date,
                SupportTicket.first_response_at.isnot(None)
            )
        ).all()

        if period_tickets:
            avg_response = sum(
                (t.first_response_at - t.created_at).total_seconds() / 60
                for t in period_tickets
            ) / len(period_tickets)
        else:
            avg_response = None

        ticket_trends.append(TicketTrend(
            date=current_date.strftime(date_format),
            count=created,
            resolved=resolved,
            avg_response_minutes=round(avg_response, 1) if avg_response else None
        ))

        current_date = next_date

    # Subscription trends (simplified - would use Stripe data in production)
    subscription_trends = []
    current_date = start_date
    while current_date <= now:
        next_date = current_date + date_delta

        new_subs = db.query(func.count(User.id)).filter(
            and_(
                User.subscription_status == "active",
                User.created_at >= current_date,
                User.created_at < next_date
            )
        ).scalar()

        # Cancellations would come from actual subscription data
        cancellations = 0

        # Revenue estimate
        revenue = new_subs * 9.99

        subscription_trends.append(SubscriptionTrend(
            date=current_date.strftime(date_format),
            new_subscriptions=new_subs,
            cancellations=cancellations,
            revenue=revenue
        ))

        current_date = next_date

    return AdminTrends(
        tickets=ticket_trends,
        subscriptions=subscription_trends,
        period=period
    )


# =============================================================================
# USER MANAGEMENT
# =============================================================================

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    subscription_status: Optional[str] = None,
    is_staff: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users with filters."""
    require_admin(current_user)

    query = db.query(User)

    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    if subscription_status:
        query = query.filter(User.subscription_status == subscription_status)

    if is_staff is not None:
        query = query.filter(User.is_staff == is_staff)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "subscription_status": u.subscription_status,
                "is_staff": u.is_staff,
                "staff_role": u.staff_role,
                "created_at": u.created_at,
                "last_login": u.last_login
            }
            for u in users
        ],
        "total": total
    }


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed user information."""
    require_admin(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get team memberships if staff
    teams = []
    if user.is_staff:
        memberships = db.query(TeamMember).filter(
            and_(TeamMember.user_id == user_id, TeamMember.is_active == True)
        ).all()
        for m in memberships:
            team = db.query(SupportTeam).filter(SupportTeam.id == m.team_id).first()
            teams.append({
                "team_id": m.team_id,
                "team_name": team.name if team else None,
                "role": m.role,
                "joined_at": m.joined_at
            })

    # Get ticket count
    ticket_count = db.query(func.count(SupportTicket.id)).filter(
        SupportTicket.user_id == user_id
    ).scalar()

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "subscription_status": user.subscription_status,
        "subscription_end_date": user.subscription_end_date,
        "trial_end_date": user.trial_end_date,
        "is_staff": user.is_staff,
        "staff_role": user.staff_role,
        "teams": teams,
        "ticket_count": ticket_count,
        "created_at": user.created_at,
        "last_login": user.last_login,
        "preferred_language": user.preferred_language,
        "email_notifications_enabled": user.email_notifications_enabled
    }


@router.patch("/users/{user_id}/staff")
async def update_user_staff_status(
    user_id: int,
    is_staff: bool,
    staff_role: Optional[str] = Query(None, pattern="^(super_admin|admin|manager|agent)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's staff status. Requires super admin."""
    if current_user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin access required")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own staff status")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_staff = is_staff
    if is_staff and staff_role:
        user.staff_role = staff_role
    elif not is_staff:
        user.staff_role = None
        # Remove from all teams
        db.query(TeamMember).filter(TeamMember.user_id == user_id).update({
            "is_active": False,
            "removed_at": datetime.utcnow()
        })

    db.commit()

    # Log activity
    log = AdminActivityLog(
        user_id=current_user.id,
        action="update_staff_status",
        entity_type="user",
        entity_id=user_id,
        details={"is_staff": is_staff, "staff_role": staff_role}
    )
    db.add(log)
    db.commit()

    return {"message": "User staff status updated"}


# =============================================================================
# ACTIVITY LOG
# =============================================================================

@router.get("/activity", response_model=List[AdminActivityLogResponse])
async def get_activity_log(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get admin activity log."""
    require_admin(current_user)

    query = db.query(AdminActivityLog)

    if user_id:
        query = query.filter(AdminActivityLog.user_id == user_id)
    if action:
        query = query.filter(AdminActivityLog.action == action)
    if entity_type:
        query = query.filter(AdminActivityLog.entity_type == entity_type)

    logs = query.order_by(AdminActivityLog.created_at.desc()).offset(offset).limit(limit).all()

    responses = []
    for log in logs:
        user = db.query(User).filter(User.id == log.user_id).first()
        responses.append(AdminActivityLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None
        ))

    return responses


# =============================================================================
# QUICK ACTIONS
# =============================================================================

@router.post("/seed-sla")
async def seed_default_sla_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seed default SLA configurations."""
    require_admin(current_user)

    from models import SLAConfig

    defaults = [
        {"priority": "urgent", "first_response_minutes": 15, "resolution_minutes": 120, "escalation_after_minutes": 30},
        {"priority": "high", "first_response_minutes": 60, "resolution_minutes": 480, "escalation_after_minutes": 120},
        {"priority": "medium", "first_response_minutes": 240, "resolution_minutes": 1440, "escalation_after_minutes": 480},
        {"priority": "low", "first_response_minutes": 480, "resolution_minutes": 2880, "escalation_after_minutes": 1440},
    ]

    created = 0
    for config in defaults:
        existing = db.query(SLAConfig).filter(SLAConfig.priority == config["priority"]).first()
        if not existing:
            sla = SLAConfig(**config)
            db.add(sla)
            created += 1

    db.commit()

    return {"message": f"Created {created} SLA configurations"}


@router.post("/seed-teams")
async def seed_default_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seed default support teams."""
    require_admin(current_user)

    defaults = [
        {"name": "Technical Support", "slug": "tech-support", "color": "#3B82F6", "description": "Help with technical issues and bugs"},
        {"name": "Sales", "slug": "sales", "color": "#10B981", "description": "Sales inquiries and enterprise deals"},
        {"name": "Accounts", "slug": "accounts", "color": "#F59E0B", "description": "Billing, payments, and account management"},
        {"name": "Customer Success", "slug": "customer-success", "color": "#8B5CF6", "description": "Onboarding and customer satisfaction"},
    ]

    created = 0
    for team_data in defaults:
        existing = db.query(SupportTeam).filter(SupportTeam.slug == team_data["slug"]).first()
        if not existing:
            team = SupportTeam(**team_data)
            db.add(team)
            created += 1

    db.commit()

    return {"message": f"Created {created} teams"}


# =============================================================================
# ORGANIZATIONS
# =============================================================================

@router.get("/organizations")
async def list_organizations(
    search: Optional[str] = None,
    plan_type: Optional[str] = None,
    subscription_status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all organizations with member counts."""
    require_admin(current_user)

    query = db.query(Organization)

    if search:
        search_filter = or_(
            Organization.name.ilike(f"%{search}%"),
            Organization.billing_email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    if plan_type:
        query = query.filter(Organization.plan_type == plan_type)

    if subscription_status:
        query = query.filter(Organization.subscription_status == subscription_status)

    total = query.count()
    organizations = query.order_by(Organization.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for org in organizations:
        # Count members
        member_count = db.query(func.count(User.id)).filter(
            User.organization_id == org.id
        ).scalar()

        # Get admin user
        admin = db.query(User).filter(User.id == org.admin_user_id).first() if org.admin_user_id else None

        result.append({
            "id": org.id,
            "name": org.name,
            "plan_type": org.plan_type,
            "max_users": org.max_users,
            "member_count": member_count,
            "subscription_status": org.subscription_status,
            "subscription_end_date": org.subscription_end_date,
            "billing_email": org.billing_email,
            "admin_email": admin.email if admin else None,
            "admin_name": admin.full_name if admin else None,
            "created_at": org.created_at
        })

    return {
        "organizations": result,
        "total": total
    }


@router.get("/organizations/{org_id}")
async def get_organization_details(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed organization info with all members."""
    require_admin(current_user)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get all members
    members = db.query(User).filter(User.organization_id == org_id).all()

    # Get admin user
    admin = db.query(User).filter(User.id == org.admin_user_id).first() if org.admin_user_id else None

    # Get ticket counts for each member
    member_list = []
    for member in members:
        ticket_count = db.query(func.count(SupportTicket.id)).filter(
            SupportTicket.user_id == member.id
        ).scalar()

        member_list.append({
            "id": member.id,
            "email": member.email,
            "full_name": member.full_name,
            "role_in_org": member.role_in_org,
            "subscription_status": member.subscription_status,
            "ticket_count": ticket_count,
            "last_login": member.last_login,
            "created_at": member.created_at
        })

    return {
        "id": org.id,
        "name": org.name,
        "plan_type": org.plan_type,
        "max_users": org.max_users,
        "subscription_status": org.subscription_status,
        "subscription_id": org.subscription_id,
        "subscription_end_date": org.subscription_end_date,
        "billing_email": org.billing_email,
        "admin_id": org.admin_user_id,
        "admin_email": admin.email if admin else None,
        "admin_name": admin.full_name if admin else None,
        "shared_insights_enabled": org.shared_insights_enabled,
        "allow_personal_professions": org.allow_personal_professions,
        "members": member_list,
        "member_count": len(member_list),
        "created_at": org.created_at,
        "updated_at": org.updated_at
    }


@router.get("/organizations/{org_id}/tickets")
async def get_organization_tickets(
    org_id: int,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all tickets from organization members."""
    require_admin(current_user)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get all member IDs
    member_ids = [m.id for m in db.query(User.id).filter(User.organization_id == org_id).all()]

    if not member_ids:
        return {"tickets": [], "total": 0}

    # Query tickets
    query = db.query(SupportTicket).filter(SupportTicket.user_id.in_(member_ids))

    if status:
        query = query.filter(SupportTicket.status == status)

    total = query.count()
    tickets = query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for ticket in tickets:
        user = db.query(User).filter(User.id == ticket.user_id).first()
        result.append({
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "category": ticket.category,
            "user_id": ticket.user_id,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        })

    return {
        "tickets": result,
        "total": total
    }
