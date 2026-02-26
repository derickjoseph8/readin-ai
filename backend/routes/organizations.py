"""Organization API routes - Corporate/Team account management."""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, OrganizationInvite, User
from schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationInviteCreate, OrganizationInviteResponse,
    OrganizationMember
)
from auth import get_current_user

logger = logging.getLogger(__name__)

# Rate limiting setup
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    # Create a no-op decorator
    class NoOpLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = NoOpLimiter()

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def get_plan_max_users(plan_type: str) -> int:
    """Get max users for a plan type."""
    limits = {
        "team": 10,
        "business": 50,
        "enterprise": 9999  # Unlimited
    }
    return limits.get(plan_type, 10)


@router.post("", response_model=OrganizationResponse)
def create_organization(
    data: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new organization (corporate account).
    The creating user becomes the admin.
    """
    # Check user doesn't already have an org
    if user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of an organization"
        )

    # Create organization
    org = Organization(
        name=data.name,
        plan_type=data.plan_type,
        max_users=get_plan_max_users(data.plan_type),
        admin_user_id=user.id,
        billing_email=data.billing_email or user.email,
        subscription_status="trial"
    )
    db.add(org)
    db.flush()

    # Add user as admin
    user.organization_id = org.id
    user.role_in_org = "admin"

    db.commit()
    db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        plan_type=org.plan_type,
        max_users=org.max_users,
        subscription_status=org.subscription_status,
        member_count=1,
        created_at=org.created_at
    )


@router.get("/my", response_model=OrganizationResponse)
@limiter.limit("30/minute") if RATE_LIMITING_AVAILABLE else lambda f: f
def get_my_organization(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's organization."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of any organization"
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    member_count = db.query(User).filter(User.organization_id == org.id).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        plan_type=org.plan_type,
        max_users=org.max_users,
        subscription_status=org.subscription_status,
        member_count=member_count,
        created_at=org.created_at
    )


@router.patch("/my", response_model=OrganizationResponse)
def update_organization(
    data: OrganizationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update organization settings. Admin only."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of any organization"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update settings"
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check organization is active
    if hasattr(org, 'subscription_status') and org.subscription_status in ['suspended', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active. Cannot update settings."
        )

    if data.name is not None:
        org.name = data.name
    if data.allow_personal_professions is not None:
        org.allow_personal_professions = data.allow_personal_professions
    if data.shared_insights_enabled is not None:
        org.shared_insights_enabled = data.shared_insights_enabled

    db.commit()
    db.refresh(org)

    member_count = db.query(User).filter(User.organization_id == org.id).count()

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        plan_type=org.plan_type,
        max_users=org.max_users,
        subscription_status=org.subscription_status,
        member_count=member_count,
        created_at=org.created_at
    )


@router.get("/my/members", response_model=List[OrganizationMember])
def list_members(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all members of the organization."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of any organization"
        )

    # Verify membership and org status
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check organization is active
    if hasattr(org, 'subscription_status') and org.subscription_status in ['suspended', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active. Contact your administrator."
        )

    members = db.query(User).filter(User.organization_id == user.organization_id).all()

    return [
        OrganizationMember(
            id=m.id,
            email=m.email,
            full_name=m.full_name,
            role_in_org=m.role_in_org,
            profession=m.profession.name if m.profession else None,
            joined_at=m.created_at
        )
        for m in members
    ]


@router.post("/my/invites", response_model=OrganizationInviteResponse)
async def create_invite(
    data: OrganizationInviteCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invite a new member to the organization.
    Admin only. Team members join for free.
    """
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of any organization"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can invite members"
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Check organization is active
    if hasattr(org, 'subscription_status') and org.subscription_status in ['suspended', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active. Cannot send invites."
        )

    # Check member limit
    current_count = db.query(User).filter(User.organization_id == org.id).count()
    pending_count = db.query(OrganizationInvite).filter(
        OrganizationInvite.organization_id == org.id,
        OrganizationInvite.status == "pending"
    ).count()

    if current_count + pending_count >= org.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization has reached maximum of {org.max_users} members. Upgrade your plan for more seats."
        )

    # Check if already invited or member
    existing_user = db.query(User).filter(
        User.email == data.email,
        User.organization_id == org.id
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already a member of your organization"
        )

    existing_invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.email == data.email,
        OrganizationInvite.organization_id == org.id,
        OrganizationInvite.status == "pending"
    ).first()
    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invite has already been sent to this email"
        )

    # Create invite
    invite = OrganizationInvite(
        organization_id=org.id,
        email=data.email,
        invited_by_id=user.id,
        role=data.role,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(days=7),
        status="pending"
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    # Send invite email asynchronously
    async def send_invite_email():
        try:
            from services.email_service import EmailService
            email_service = EmailService(db)
            inviter_name = user.full_name or user.email
            await email_service.send_organization_invite(
                to_email=data.email,
                organization_name=org.name,
                inviter_name=inviter_name,
                invite_token=invite.token,
                role=data.role,
            )
            logger.info(f"Invite email sent to {data.email} for org {org.name}")
        except Exception as e:
            logger.error(f"Failed to send invite email to {data.email}: {e}")

    background_tasks.add_task(asyncio.create_task, send_invite_email())

    return OrganizationInviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at
    )


@router.get("/my/invites", response_model=List[OrganizationInviteResponse])
def list_invites(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pending invites for the organization. Admin only."""
    if not user.organization_id or user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can view invites"
        )

    invites = db.query(OrganizationInvite).filter(
        OrganizationInvite.organization_id == user.organization_id,
        OrganizationInvite.status == "pending"
    ).order_by(OrganizationInvite.created_at.desc()).all()

    return [
        OrganizationInviteResponse(
            id=i.id,
            email=i.email,
            role=i.role,
            status=i.status,
            expires_at=i.expires_at,
            created_at=i.created_at
        )
        for i in invites
    ]


@router.delete("/my/invites/{invite_id}")
def cancel_invite(
    invite_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending invite. Admin only."""
    if not user.organization_id or user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can cancel invites"
        )

    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.id == invite_id,
        OrganizationInvite.organization_id == user.organization_id
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found"
        )

    invite.status = "cancelled"
    db.commit()

    return {"message": "Invite cancelled"}


@router.post("/join/{token}")
def join_organization(
    token: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accept an organization invite and join the team.
    User joins for FREE - admin pays for all seats.
    """
    if user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of an organization. Leave first to join another."
        )

    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.token == token,
        OrganizationInvite.status == "pending"
    ).first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invite"
        )

    # Check email matches
    if invite.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invite was sent to a different email address"
        )

    # Check not expired
    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired"
        )

    # Join organization
    user.organization_id = invite.organization_id
    user.role_in_org = invite.role

    # Mark invite as accepted
    invite.status = "accepted"
    invite.accepted_at = datetime.utcnow()

    db.commit()

    org = db.query(Organization).filter(Organization.id == invite.organization_id).first()

    return {
        "message": f"Welcome to {org.name}!",
        "organization_name": org.name,
        "role": invite.role
    }


@router.delete("/my/members/{member_id}")
def remove_member(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the organization. Admin only."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of any organization"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can remove members"
        )

    # Check organization is active
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if org and hasattr(org, 'subscription_status') and org.subscription_status in ['suspended', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active. Cannot remove members."
        )

    if member_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Transfer admin role first or delete organization."
        )

    member = db.query(User).filter(
        User.id == member_id,
        User.organization_id == user.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in your organization"
        )

    member.organization_id = None
    member.role_in_org = None
    db.commit()

    return {"message": f"Member {member.email} has been removed"}


@router.post("/leave")
def leave_organization(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave the current organization."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not a member of any organization"
        )

    org = db.query(Organization).filter(Organization.id == user.organization_id).first()

    # Check if admin
    if user.role_in_org == "admin":
        # Check if other admins exist
        other_admins = db.query(User).filter(
            User.organization_id == org.id,
            User.role_in_org == "admin",
            User.id != user.id
        ).count()

        if other_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are the only admin. Transfer admin role to another member before leaving."
            )

    user.organization_id = None
    user.role_in_org = None
    db.commit()

    return {"message": f"You have left {org.name}"}


@router.post("/my/members/{member_id}/make-admin")
def make_admin(
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Promote a member to admin. Admin only."""
    if not user.organization_id or user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can promote members"
        )

    member = db.query(User).filter(
        User.id == member_id,
        User.organization_id == user.organization_id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in your organization"
        )

    member.role_in_org = "admin"
    db.commit()

    return {"message": f"{member.email} is now an admin"}
