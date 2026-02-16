"""
Admin routes for team management.
Super admin can add/remove admins, admins can manage other roles.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import secrets

from database import get_db
from auth import get_current_user
from models import (
    User, SupportTeam, TeamMember, TeamInvite, AgentStatus,
    StaffRole, AdminActivityLog
)
from schemas import (
    SupportTeamCreate, SupportTeamUpdate, SupportTeamResponse, SupportTeamList,
    TeamMemberCreate, TeamMemberInvite, TeamMemberResponse, TeamMemberList,
    TeamInviteResponse
)

router = APIRouter(prefix="/admin/teams", tags=["Admin - Teams"])


def require_staff(user: User):
    """Verify user is a staff member."""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Staff access required")


def require_admin(user: User):
    """Verify user is admin or super_admin."""
    if not user.is_staff or user.staff_role not in [StaffRole.SUPER_ADMIN, StaffRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")


def require_super_admin(user: User):
    """Verify user is super_admin."""
    if not user.is_staff or user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super admin access required")


def log_activity(db: Session, user_id: int, action: str, entity_type: str,
                 entity_id: int = None, details: dict = None):
    """Log admin activity."""
    log = AdminActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    db.add(log)
    db.commit()


# =============================================================================
# TEAM CRUD
# =============================================================================

@router.get("/", response_model=SupportTeamList)
async def list_teams(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all support teams."""
    require_staff(current_user)

    query = db.query(SupportTeam)
    if not include_inactive:
        query = query.filter(SupportTeam.is_active == True)

    teams = query.order_by(SupportTeam.name).all()

    # Add member counts
    team_responses = []
    for team in teams:
        member_count = db.query(func.count(TeamMember.id)).filter(
            and_(TeamMember.team_id == team.id, TeamMember.is_active == True)
        ).scalar()

        team_dict = {
            **team.__dict__,
            "member_count": member_count
        }
        team_responses.append(SupportTeamResponse(**team_dict))

    return SupportTeamList(teams=team_responses, total=len(team_responses))


@router.post("/", response_model=SupportTeamResponse, status_code=201)
async def create_team(
    team_data: SupportTeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new support team. Requires admin."""
    require_admin(current_user)

    # Check if slug exists
    existing = db.query(SupportTeam).filter(
        SupportTeam.slug == team_data.slug
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team slug already exists")

    team = SupportTeam(**team_data.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)

    log_activity(db, current_user.id, "create_team", "team", team.id,
                 {"name": team.name})

    return SupportTeamResponse(**{**team.__dict__, "member_count": 0})


@router.get("/{team_id}", response_model=SupportTeamResponse)
async def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get team details."""
    require_staff(current_user)

    team = db.query(SupportTeam).filter(SupportTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    member_count = db.query(func.count(TeamMember.id)).filter(
        and_(TeamMember.team_id == team.id, TeamMember.is_active == True)
    ).scalar()

    return SupportTeamResponse(**{**team.__dict__, "member_count": member_count})


@router.patch("/{team_id}", response_model=SupportTeamResponse)
async def update_team(
    team_id: int,
    update_data: SupportTeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update team settings. Requires admin."""
    require_admin(current_user)

    team = db.query(SupportTeam).filter(SupportTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(team, field, value)

    team.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(team)

    log_activity(db, current_user.id, "update_team", "team", team.id,
                 update_data.model_dump(exclude_unset=True))

    member_count = db.query(func.count(TeamMember.id)).filter(
        and_(TeamMember.team_id == team.id, TeamMember.is_active == True)
    ).scalar()

    return SupportTeamResponse(**{**team.__dict__, "member_count": member_count})


@router.delete("/{team_id}")
async def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a team (set inactive). Requires super admin."""
    require_super_admin(current_user)

    team = db.query(SupportTeam).filter(SupportTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    team.is_active = False
    team.updated_at = datetime.utcnow()
    db.commit()

    log_activity(db, current_user.id, "delete_team", "team", team.id)

    return {"message": "Team deactivated successfully"}


# =============================================================================
# TEAM MEMBERS
# =============================================================================

@router.get("/{team_id}/members", response_model=TeamMemberList)
async def list_team_members(
    team_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List members of a team."""
    require_staff(current_user)

    team = db.query(SupportTeam).filter(SupportTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    query = db.query(TeamMember).filter(TeamMember.team_id == team_id)
    if not include_inactive:
        query = query.filter(TeamMember.is_active == True)

    members = query.all()

    member_responses = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        member_responses.append(TeamMemberResponse(
            id=member.id,
            user_id=member.user_id,
            team_id=member.team_id,
            role=member.role,
            is_active=member.is_active,
            joined_at=member.joined_at,
            user_email=user.email if user else None,
            user_name=user.full_name if user else None,
            team_name=team.name
        ))

    return TeamMemberList(members=member_responses, total=len(member_responses))


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=201)
async def add_team_member(
    team_id: int,
    member_data: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add an existing user to a team. Requires admin."""
    require_admin(current_user)

    # Only super admin can add admins
    if member_data.role == StaffRole.ADMIN and current_user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can add team admins")

    team = db.query(SupportTeam).filter(SupportTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user = db.query(User).filter(User.id == member_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = db.query(TeamMember).filter(
        and_(
            TeamMember.user_id == member_data.user_id,
            TeamMember.team_id == team_id
        )
    ).first()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="User is already a team member")
        # Reactivate
        existing.is_active = True
        existing.role = member_data.role
        existing.removed_at = None
        db.commit()
        db.refresh(existing)
        member = existing
    else:
        member = TeamMember(
            user_id=member_data.user_id,
            team_id=team_id,
            role=member_data.role,
            invited_by_id=current_user.id
        )
        db.add(member)
        db.commit()
        db.refresh(member)

    # Update user's staff status
    user.is_staff = True
    if not user.staff_role or user.staff_role == StaffRole.AGENT:
        user.staff_role = member_data.role
    db.commit()

    # Create agent status for chat
    agent_status = db.query(AgentStatus).filter(
        AgentStatus.team_member_id == member.id
    ).first()
    if not agent_status:
        agent_status = AgentStatus(team_member_id=member.id)
        db.add(agent_status)
        db.commit()

    log_activity(db, current_user.id, "add_team_member", "team_member", member.id,
                 {"user_id": user.id, "team_id": team_id, "role": member_data.role})

    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        team_id=member.team_id,
        role=member.role,
        is_active=member.is_active,
        joined_at=member.joined_at,
        user_email=user.email,
        user_name=user.full_name,
        team_name=team.name
    )


@router.delete("/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from a team. Requires admin."""
    require_admin(current_user)

    member = db.query(TeamMember).filter(
        and_(TeamMember.id == member_id, TeamMember.team_id == team_id)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    # Only super admin can remove admins
    if member.role == StaffRole.ADMIN and current_user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can remove team admins")

    member.is_active = False
    member.removed_at = datetime.utcnow()
    db.commit()

    # Check if user is still on any team
    other_teams = db.query(TeamMember).filter(
        and_(
            TeamMember.user_id == member.user_id,
            TeamMember.is_active == True,
            TeamMember.id != member_id
        )
    ).count()

    if other_teams == 0:
        # Remove staff status
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            user.is_staff = False
            user.staff_role = None
            db.commit()

    log_activity(db, current_user.id, "remove_team_member", "team_member", member_id,
                 {"user_id": member.user_id, "team_id": team_id})

    return {"message": "Team member removed successfully"}


@router.patch("/{team_id}/members/{member_id}/role")
async def update_member_role(
    team_id: int,
    member_id: int,
    role: str = Query(..., pattern="^(admin|manager|agent)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a member's role. Requires admin (super admin for admin role)."""
    require_admin(current_user)

    member = db.query(TeamMember).filter(
        and_(TeamMember.id == member_id, TeamMember.team_id == team_id)
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    # Only super admin can promote to/demote from admin
    if (role == StaffRole.ADMIN or member.role == StaffRole.ADMIN) and \
       current_user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can manage admin roles")

    old_role = member.role
    member.role = role
    db.commit()

    # Update user's staff role if this is their highest role
    user = db.query(User).filter(User.id == member.user_id).first()
    if user:
        # Get highest role across all teams
        all_roles = db.query(TeamMember.role).filter(
            and_(TeamMember.user_id == user.id, TeamMember.is_active == True)
        ).all()
        roles = [r[0] for r in all_roles]

        if StaffRole.ADMIN in roles:
            user.staff_role = StaffRole.ADMIN
        elif StaffRole.MANAGER in roles:
            user.staff_role = StaffRole.MANAGER
        else:
            user.staff_role = StaffRole.AGENT
        db.commit()

    log_activity(db, current_user.id, "update_member_role", "team_member", member_id,
                 {"old_role": old_role, "new_role": role})

    return {"message": f"Member role updated to {role}"}


# =============================================================================
# INVITATIONS
# =============================================================================

@router.post("/invite", response_model=TeamInviteResponse, status_code=201)
async def invite_team_member(
    invite_data: TeamMemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send invitation to join a team. Requires admin."""
    require_admin(current_user)

    # Only super admin can invite admins
    if invite_data.role == StaffRole.ADMIN and current_user.staff_role != StaffRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only super admin can invite team admins")

    team = db.query(SupportTeam).filter(SupportTeam.id == invite_data.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check for existing pending invite
    existing = db.query(TeamInvite).filter(
        and_(
            TeamInvite.email == invite_data.email,
            TeamInvite.team_id == invite_data.team_id,
            TeamInvite.status == "pending"
        )
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Pending invitation already exists for this email")

    # Check if user already exists and is a member
    existing_user = db.query(User).filter(User.email == invite_data.email).first()
    if existing_user:
        existing_member = db.query(TeamMember).filter(
            and_(
                TeamMember.user_id == existing_user.id,
                TeamMember.team_id == invite_data.team_id,
                TeamMember.is_active == True
            )
        ).first()
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a team member")

    invite = TeamInvite(
        team_id=invite_data.team_id,
        email=invite_data.email,
        role=invite_data.role,
        token=secrets.token_urlsafe(32),
        invited_by_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    log_activity(db, current_user.id, "create_invite", "team_invite", invite.id,
                 {"email": invite_data.email, "team_id": invite_data.team_id})

    # TODO: Send invitation email

    return TeamInviteResponse(
        id=invite.id,
        team_id=invite.team_id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        team_name=team.name
    )


@router.get("/invites/pending", response_model=List[TeamInviteResponse])
async def list_pending_invites(
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List pending invitations."""
    require_admin(current_user)

    query = db.query(TeamInvite).filter(
        and_(
            TeamInvite.status == "pending",
            TeamInvite.expires_at > datetime.utcnow()
        )
    )

    if team_id:
        query = query.filter(TeamInvite.team_id == team_id)

    invites = query.order_by(TeamInvite.created_at.desc()).all()

    responses = []
    for invite in invites:
        team = db.query(SupportTeam).filter(SupportTeam.id == invite.team_id).first()
        responses.append(TeamInviteResponse(
            id=invite.id,
            team_id=invite.team_id,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            expires_at=invite.expires_at,
            created_at=invite.created_at,
            team_name=team.name if team else None
        ))

    return responses


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending invitation."""
    require_admin(current_user)

    invite = db.query(TeamInvite).filter(
        and_(TeamInvite.id == invite_id, TeamInvite.status == "pending")
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invite.status = "cancelled"
    db.commit()

    log_activity(db, current_user.id, "cancel_invite", "team_invite", invite_id)

    return {"message": "Invitation cancelled"}


@router.post("/invites/{token}/accept")
async def accept_invite(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a team invitation."""
    invite = db.query(TeamInvite).filter(
        and_(
            TeamInvite.token == token,
            TeamInvite.status == "pending",
            TeamInvite.expires_at > datetime.utcnow()
        )
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    if invite.email.lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="This invitation is for a different email")

    # Check if already a member
    existing = db.query(TeamMember).filter(
        and_(
            TeamMember.user_id == current_user.id,
            TeamMember.team_id == invite.team_id
        )
    ).first()

    if existing:
        if existing.is_active:
            invite.status = "accepted"
            db.commit()
            return {"message": "Already a team member"}
        # Reactivate
        existing.is_active = True
        existing.role = invite.role
        existing.removed_at = None
    else:
        member = TeamMember(
            user_id=current_user.id,
            team_id=invite.team_id,
            role=invite.role,
            invited_by_id=invite.invited_by_id
        )
        db.add(member)

    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()

    # Update user staff status
    current_user.is_staff = True
    if not current_user.staff_role:
        current_user.staff_role = invite.role

    db.commit()

    log_activity(db, current_user.id, "accept_invite", "team_invite", invite.id)

    return {"message": "Successfully joined the team"}
