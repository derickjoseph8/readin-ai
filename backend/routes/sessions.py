"""Session management routes for viewing and revoking user sessions."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSession
from auth import get_current_user
from services.audit_logger import AuditLogger, get_client_ip, get_user_agent

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SessionResponse(BaseModel):
    """Response schema for a user session."""
    id: int
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    ip_address: Optional[str] = None
    location: Optional[str] = None
    is_current: bool
    last_activity: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""
    sessions: List[SessionResponse]
    current_session_id: Optional[int] = None
    total_active: int


class RevokeSessionRequest(BaseModel):
    """Request to revoke a specific session."""
    session_id: int


class RevokeAllResponse(BaseModel):
    """Response for revoke all sessions."""
    revoked_count: int
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=SessionListResponse)
def get_user_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all active sessions for the current user.

    Returns list of active sessions with device information.
    """
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True,
    ).order_by(UserSession.last_activity.desc()).all()

    # Find current session
    current_ip = get_client_ip(request)
    current_session = None
    for session in sessions:
        if session.ip_address == current_ip:
            current_session = session
            break

    return SessionListResponse(
        sessions=[SessionResponse.model_validate(s) for s in sessions],
        current_session_id=current_session.id if current_session else None,
        total_active=len(sessions),
    )


@router.post("/{session_id}/revoke")
def revoke_session(
    session_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a specific session.

    Immediately invalidates the session token.
    """
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user.id,
        UserSession.is_active == True,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked",
        )

    # Mark session as revoked
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    db.commit()

    # Log the action
    AuditLogger.log(
        db=db,
        action="session_revoke",
        user_id=user.id,
        resource_type="UserSession",
        resource_id=session_id,
        ip_address=get_client_ip(request),
        details={"device": session.device_name},
    )

    return {"message": "Session revoked successfully", "session_id": session_id}


@router.post("/revoke-all", response_model=RevokeAllResponse)
def revoke_all_sessions(
    request: Request,
    keep_current: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke all active sessions.

    By default keeps the current session active. Set keep_current=False
    to revoke all sessions including the current one.
    """
    current_ip = get_client_ip(request)

    query = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True,
    )

    if keep_current:
        # Exclude current session
        query = query.filter(UserSession.ip_address != current_ip)

    sessions = query.all()
    revoked_count = 0

    for session in sessions:
        session.is_active = False
        session.revoked_at = datetime.utcnow()
        revoked_count += 1

    db.commit()

    # Log the action
    AuditLogger.log(
        db=db,
        action="session_revoke_all",
        user_id=user.id,
        ip_address=current_ip,
        details={"revoked_count": revoked_count, "kept_current": keep_current},
    )

    return RevokeAllResponse(
        revoked_count=revoked_count,
        message=f"Successfully revoked {revoked_count} session(s)",
    )


@router.get("/current")
def get_current_session(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get information about the current session.
    """
    current_ip = get_client_ip(request)

    session = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.ip_address == current_ip,
        UserSession.is_active == True,
    ).first()

    if not session:
        return {
            "message": "No session tracking available",
            "ip_address": current_ip,
        }

    return SessionResponse.model_validate(session)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_session(
    db: Session,
    user: User,
    request: Request,
    session_token: str,
    expires_at: Optional[datetime] = None,
) -> UserSession:
    """
    Create a new session for a user.

    Called during login to track the new session.
    """
    user_agent = get_user_agent(request)
    ip_address = get_client_ip(request)

    # Parse user agent for device info (simplified)
    device_type = "desktop"
    browser = None
    os = None

    if user_agent:
        ua_lower = user_agent.lower()
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"

        # Simple browser detection
        if "chrome" in ua_lower:
            browser = "Chrome"
        elif "firefox" in ua_lower:
            browser = "Firefox"
        elif "safari" in ua_lower:
            browser = "Safari"
        elif "edge" in ua_lower:
            browser = "Edge"

        # Simple OS detection
        if "windows" in ua_lower:
            os = "Windows"
        elif "mac" in ua_lower:
            os = "macOS"
        elif "linux" in ua_lower:
            os = "Linux"
        elif "android" in ua_lower:
            os = "Android"
        elif "ios" in ua_lower or "iphone" in ua_lower:
            os = "iOS"

    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        device_type=device_type,
        browser=browser,
        os=os,
        ip_address=ip_address,
        is_active=True,
        is_current=True,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def update_session_activity(
    db: Session,
    session_token: str,
    ip_address: Optional[str] = None,
):
    """
    Update session last activity time.

    Called during authenticated requests to track activity.
    """
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == True,
    ).first()

    if session:
        session.last_activity = datetime.utcnow()
        if ip_address:
            session.last_ip = ip_address
        db.commit()


def cleanup_expired_sessions(db: Session):
    """
    Clean up expired sessions.

    Should be called periodically by a background job.
    """
    now = datetime.utcnow()

    expired = db.query(UserSession).filter(
        UserSession.expires_at < now,
        UserSession.is_active == True,
    ).all()

    for session in expired:
        session.is_active = False
        session.revoked_at = now

    db.commit()

    return len(expired)
