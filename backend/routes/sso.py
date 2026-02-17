"""
Single Sign-On (SSO) API routes.

Provides endpoints for:
- SAML 2.0 authentication
- OAuth 2.0 / OpenID Connect (OIDC)
- Azure AD integration
- Okta integration
- Direct social login (Google, Microsoft, Apple)
"""

import os
import secrets
import hashlib
import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from database import get_db
from models import (
    User, Organization, SSOProvider, SSOSession,
    Role, UserRole, AuditLog, AuditAction
)
from auth import get_current_user, create_access_token
from config import JWT_ALGORITHM, JWT_SECRET, JWT_EXPIRATION_HOURS

# Social login OAuth configurations (from environment)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.getreadin.us")
BACKEND_URL = os.getenv("BACKEND_URL", "https://www.getreadin.us")

router = APIRouter(prefix="/sso", tags=["SSO"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class SSOProviderCreate(BaseModel):
    """Create SSO provider request."""
    name: str
    provider_type: str  # saml, oidc, azure_ad, okta, google
    # SAML settings
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_certificate: Optional[str] = None
    saml_metadata_url: Optional[str] = None
    # OIDC settings
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None
    # Options
    auto_provision_users: bool = True
    allowed_domains: List[str] = []


class SSOProviderUpdate(BaseModel):
    """Update SSO provider request."""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_certificate: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    auto_provision_users: Optional[bool] = None
    allowed_domains: Optional[List[str]] = None


class SSOProviderResponse(BaseModel):
    """SSO provider response."""
    id: int
    organization_id: int
    name: str
    provider_type: str
    is_active: bool
    is_default: bool
    auto_provision_users: bool
    allowed_domains: List[str]
    created_at: datetime


class SSOInitiateRequest(BaseModel):
    """Initiate SSO login request."""
    provider_id: int
    redirect_uri: Optional[str] = None


class SSOInitiateResponse(BaseModel):
    """SSO initiation response."""
    auth_url: str
    state: str


class SSOCallbackRequest(BaseModel):
    """SSO callback request for OIDC."""
    code: str
    state: str


class SAMLCallbackRequest(BaseModel):
    """SAML callback request."""
    saml_response: str
    relay_state: Optional[str] = None


class SSOSessionResponse(BaseModel):
    """SSO session info response."""
    id: int
    provider_name: str
    provider_type: str
    created_at: datetime
    last_activity: datetime
    is_active: bool


# =============================================================================
# SSO PROVIDER MANAGEMENT
# =============================================================================

@router.get("/providers", response_model=List[SSOProviderResponse])
def list_sso_providers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List SSO providers for the user's organization.

    Requires: Organization admin or SSO management permission.
    """
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is only available for organizations"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can manage SSO"
        )

    providers = db.query(SSOProvider).filter(
        SSOProvider.organization_id == user.organization_id
    ).all()

    return [
        SSOProviderResponse(
            id=p.id,
            organization_id=p.organization_id,
            name=p.name,
            provider_type=p.provider_type,
            is_active=p.is_active,
            is_default=p.is_default,
            auto_provision_users=p.auto_provision_users,
            allowed_domains=p.allowed_domains or [],
            created_at=p.created_at
        )
        for p in providers
    ]


@router.post("/providers", response_model=SSOProviderResponse, status_code=status.HTTP_201_CREATED)
def create_sso_provider(
    request: SSOProviderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new SSO provider for the organization.

    Supported provider types:
    - `saml`: SAML 2.0
    - `oidc`: Generic OpenID Connect
    - `azure_ad`: Microsoft Azure Active Directory
    - `okta`: Okta
    - `google`: Google Workspace
    """
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is only available for organizations"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can manage SSO"
        )

    # Validate provider type
    valid_types = ["saml", "oidc", "azure_ad", "okta", "google"]
    if request.provider_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider type. Must be one of: {', '.join(valid_types)}"
        )

    # Check for existing provider of same type
    existing = db.query(SSOProvider).filter(
        SSOProvider.organization_id == user.organization_id,
        SSOProvider.provider_type == request.provider_type
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A {request.provider_type} provider already exists for this organization"
        )

    # Create provider
    provider = SSOProvider(
        organization_id=user.organization_id,
        name=request.name,
        provider_type=request.provider_type,
        saml_entity_id=request.saml_entity_id,
        saml_sso_url=request.saml_sso_url,
        saml_certificate=request.saml_certificate,
        saml_metadata_url=request.saml_metadata_url,
        oidc_client_id=request.oidc_client_id,
        oidc_client_secret=request.oidc_client_secret,
        oidc_discovery_url=request.oidc_discovery_url,
        auto_provision_users=request.auto_provision_users,
        allowed_domains=request.allowed_domains
    )

    db.add(provider)
    db.commit()
    db.refresh(provider)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="sso_provider_create",
        resource_type="SSOProvider",
        resource_id=provider.id,
        details={"provider_type": request.provider_type, "name": request.name}
    )
    db.add(audit)
    db.commit()

    return SSOProviderResponse(
        id=provider.id,
        organization_id=provider.organization_id,
        name=provider.name,
        provider_type=provider.provider_type,
        is_active=provider.is_active,
        is_default=provider.is_default,
        auto_provision_users=provider.auto_provision_users,
        allowed_domains=provider.allowed_domains or [],
        created_at=provider.created_at
    )


@router.put("/providers/{provider_id}", response_model=SSOProviderResponse)
def update_sso_provider(
    provider_id: int,
    request: SSOProviderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an SSO provider configuration."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is only available for organizations"
        )

    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.organization_id == user.organization_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO provider not found"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can manage SSO"
        )

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    provider.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(provider)

    return SSOProviderResponse(
        id=provider.id,
        organization_id=provider.organization_id,
        name=provider.name,
        provider_type=provider.provider_type,
        is_active=provider.is_active,
        is_default=provider.is_default,
        auto_provision_users=provider.auto_provision_users,
        allowed_domains=provider.allowed_domains or [],
        created_at=provider.created_at
    )


@router.delete("/providers/{provider_id}")
def delete_sso_provider(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an SSO provider."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO is only available for organizations"
        )

    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id,
        SSOProvider.organization_id == user.organization_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO provider not found"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can manage SSO"
        )

    # Terminate active sessions
    db.query(SSOSession).filter(
        SSOSession.provider_id == provider_id,
        SSOSession.is_active == True
    ).update({"is_active": False, "terminated_at": datetime.utcnow()})

    # Delete provider
    db.delete(provider)
    db.commit()

    return {"status": "success", "message": "SSO provider deleted"}


# =============================================================================
# SSO AUTHENTICATION FLOW
# =============================================================================

@router.post("/initiate", response_model=SSOInitiateResponse)
def initiate_sso_login(
    request: SSOInitiateRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate SSO login flow.

    Returns the authorization URL to redirect the user to.
    """
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == request.provider_id,
        SSOProvider.is_active == True
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO provider not found or inactive"
        )

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)

    # Build auth URL based on provider type
    if provider.provider_type == "saml":
        # For SAML, return the SSO URL with state
        auth_url = f"{provider.saml_sso_url}?RelayState={state}"

    elif provider.provider_type in ["oidc", "azure_ad", "okta", "google"]:
        # OIDC flow
        redirect_uri = request.redirect_uri or "https://www.getreadin.us/sso/callback"
        scopes = " ".join(provider.oidc_scopes or ["openid", "email", "profile"])

        if provider.provider_type == "azure_ad":
            # Azure AD specific URL
            auth_url = (
                f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
                f"?client_id={provider.oidc_client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope={scopes}"
                f"&state={state}"
                f"&response_mode=query"
            )
        elif provider.provider_type == "okta":
            # Okta specific URL
            auth_url = (
                f"{provider.oidc_authorization_url or provider.oidc_discovery_url.replace('/.well-known/openid-configuration', '/v1/authorize')}"
                f"?client_id={provider.oidc_client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope={scopes}"
                f"&state={state}"
            )
        elif provider.provider_type == "google":
            # Google Workspace
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth"
                f"?client_id={provider.oidc_client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope={scopes}"
                f"&state={state}"
                f"&access_type=offline"
            )
        else:
            # Generic OIDC
            auth_url = (
                f"{provider.oidc_authorization_url}"
                f"?client_id={provider.oidc_client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope={scopes}"
                f"&state={state}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider type: {provider.provider_type}"
        )

    return SSOInitiateResponse(auth_url=auth_url, state=state)


@router.get("/callback")
def sso_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle OIDC callback after user authentication.

    Exchanges the authorization code for tokens and creates/updates the user.
    """
    # In a real implementation, you would:
    # 1. Validate the state token
    # 2. Exchange the code for tokens with the IdP
    # 3. Validate the ID token
    # 4. Extract user info from the token
    # 5. Create or update the user
    # 6. Create an SSO session
    # 7. Return a JWT token

    # This is a simplified implementation for demonstration
    return {
        "message": "SSO callback received",
        "note": "Full implementation requires IdP token exchange",
        "code_received": bool(code),
        "state_received": bool(state)
    }


@router.post("/saml/callback")
def saml_callback(
    request: SAMLCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle SAML assertion callback.

    Validates the SAML response and creates/updates the user.
    """
    # In a real implementation, you would:
    # 1. Decode and validate the SAML response
    # 2. Verify the signature using the IdP certificate
    # 3. Extract user attributes
    # 4. Create or update the user
    # 5. Create an SSO session
    # 6. Return a JWT token

    return {
        "message": "SAML callback received",
        "note": "Full implementation requires SAML response parsing",
        "response_received": bool(request.saml_response)
    }


# =============================================================================
# SSO SESSION MANAGEMENT
# =============================================================================

@router.get("/sessions", response_model=List[SSOSessionResponse])
def list_sso_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List active SSO sessions for the current user."""
    sessions = db.query(SSOSession).join(SSOProvider).filter(
        SSOSession.user_id == user.id,
        SSOSession.is_active == True
    ).all()

    return [
        SSOSessionResponse(
            id=s.id,
            provider_name=s.provider.name,
            provider_type=s.provider.provider_type,
            created_at=s.created_at,
            last_activity=s.last_activity,
            is_active=s.is_active
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def terminate_sso_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate a specific SSO session."""
    session = db.query(SSOSession).filter(
        SSOSession.id == session_id,
        SSOSession.user_id == user.id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO session not found"
        )

    session.is_active = False
    session.terminated_at = datetime.utcnow()
    db.commit()

    return {"status": "success", "message": "SSO session terminated"}


@router.post("/sessions/terminate-all")
def terminate_all_sso_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Terminate all SSO sessions for the current user."""
    db.query(SSOSession).filter(
        SSOSession.user_id == user.id,
        SSOSession.is_active == True
    ).update({
        "is_active": False,
        "terminated_at": datetime.utcnow()
    })
    db.commit()

    return {"status": "success", "message": "All SSO sessions terminated"}


# =============================================================================
# SSO METADATA ENDPOINTS
# =============================================================================

@router.get("/metadata/{provider_id}")
def get_sso_metadata(
    provider_id: int,
    db: Session = Depends(get_db)
):
    """
    Get SSO metadata for service provider configuration.

    Returns SAML SP metadata or OIDC discovery info.
    """
    provider = db.query(SSOProvider).filter(
        SSOProvider.id == provider_id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO provider not found"
        )

    base_url = "https://www.getreadin.us"

    if provider.provider_type == "saml":
        # Return SAML SP metadata
        return {
            "entity_id": f"{base_url}/sso/saml/metadata",
            "assertion_consumer_service_url": f"{base_url}/sso/saml/callback",
            "single_logout_url": f"{base_url}/sso/saml/logout",
            "name_id_format": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
        }
    else:
        # Return OIDC callback info
        return {
            "callback_url": f"{base_url}/sso/callback",
            "logout_url": f"{base_url}/sso/logout",
            "supported_scopes": ["openid", "email", "profile"]
        }


# =============================================================================
# DIRECT SOCIAL LOGIN (Google, Microsoft, Apple)
# =============================================================================

# In-memory state storage (use Redis in production)
_sso_states = {}


@router.get("/google/initiate")
def initiate_google_login(
    redirect_uri: Optional[str] = None,
    calendar_access: bool = False
):
    """
    Initiate Google OAuth login.

    Args:
        redirect_uri: Optional custom redirect after login
        calendar_access: If True, request calendar read access
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google SSO is not configured"
        )

    state = secrets.token_urlsafe(32)
    _sso_states[state] = {
        "provider": "google",
        "redirect_uri": redirect_uri,
        "created_at": datetime.utcnow()
    }

    callback_url = f"{BACKEND_URL}/api/v1/sso/google/callback"
    scopes = ["openid", "email", "profile"]

    if calendar_access:
        scopes.append("https://www.googleapis.com/auth/calendar.readonly")
        _sso_states[state]["calendar_access"] = True

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&scope={' '.join(scopes)}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    # Validate state
    state_data = _sso_states.pop(state, None)
    if not state_data or state_data["provider"] != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state"
        )

    callback_url = f"{BACKEND_URL}/api/v1/sso/google/callback"

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens"
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        # Get user info
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )

        userinfo = userinfo_response.json()

    # Find or create user
    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=userinfo.get("name"),
            hashed_password="",  # No password for SSO users
            is_active=True,
            email_verified=True,
            sso_provider="google",
            sso_provider_id=userinfo.get("id")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update SSO info if not set
        if not user.sso_provider:
            user.sso_provider = "google"
            user.sso_provider_id = userinfo.get("id")
            db.commit()

    # Store refresh token for calendar access if requested
    if state_data.get("calendar_access") and refresh_token:
        user.google_refresh_token = refresh_token
        db.commit()

    # Create JWT token
    jwt_token = create_access_token(user.id)

    # Redirect to frontend with token
    redirect_uri = state_data.get("redirect_uri") or f"{FRONTEND_URL}/sso/callback"
    return RedirectResponse(url=f"{redirect_uri}?token={jwt_token}")


@router.get("/microsoft/initiate")
def initiate_microsoft_login(
    redirect_uri: Optional[str] = None,
    calendar_access: bool = False
):
    """
    Initiate Microsoft OAuth login.

    Args:
        redirect_uri: Optional custom redirect after login
        calendar_access: If True, request calendar read access
    """
    if not MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Microsoft SSO is not configured"
        )

    state = secrets.token_urlsafe(32)
    _sso_states[state] = {
        "provider": "microsoft",
        "redirect_uri": redirect_uri,
        "created_at": datetime.utcnow()
    }

    callback_url = f"{BACKEND_URL}/api/v1/sso/microsoft/callback"
    scopes = ["openid", "email", "profile", "User.Read"]

    if calendar_access:
        scopes.append("Calendars.Read")
        _sso_states[state]["calendar_access"] = True

    auth_url = (
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        f"?client_id={MICROSOFT_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&scope={' '.join(scopes)}"
        f"&state={state}"
        f"&response_mode=query"
    )

    return RedirectResponse(url=auth_url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Microsoft OAuth callback."""
    # Validate state
    state_data = _sso_states.pop(state, None)
    if not state_data or state_data["provider"] != "microsoft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state"
        )

    callback_url = f"{BACKEND_URL}/api/v1/sso/microsoft/callback"

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens"
            )

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        # Get user info from Microsoft Graph
        userinfo_response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info"
            )

        userinfo = userinfo_response.json()

    # Find or create user
    email = userinfo.get("mail") or userinfo.get("userPrincipalName")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Microsoft"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=userinfo.get("displayName"),
            hashed_password="",
            is_active=True,
            email_verified=True,
            sso_provider="microsoft",
            sso_provider_id=userinfo.get("id")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.sso_provider:
            user.sso_provider = "microsoft"
            user.sso_provider_id = userinfo.get("id")
            db.commit()

    # Store refresh token for calendar access
    if state_data.get("calendar_access") and refresh_token:
        user.microsoft_refresh_token = refresh_token
        db.commit()

    # Create JWT token
    jwt_token = create_access_token(user.id)

    # Redirect to frontend with token
    redirect_uri = state_data.get("redirect_uri") or f"{FRONTEND_URL}/sso/callback"
    return RedirectResponse(url=f"{redirect_uri}?token={jwt_token}")


@router.get("/apple/initiate")
def initiate_apple_login(redirect_uri: Optional[str] = None):
    """
    Initiate Apple Sign In.

    Note: Apple Sign In requires additional setup with Apple Developer account.
    """
    if not APPLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple SSO is not configured"
        )

    state = secrets.token_urlsafe(32)
    _sso_states[state] = {
        "provider": "apple",
        "redirect_uri": redirect_uri,
        "created_at": datetime.utcnow()
    }

    callback_url = f"{BACKEND_URL}/api/v1/sso/apple/callback"

    auth_url = (
        f"https://appleid.apple.com/auth/authorize"
        f"?client_id={APPLE_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={callback_url}"
        f"&scope=name email"
        f"&state={state}"
        f"&response_mode=form_post"
    )

    return RedirectResponse(url=auth_url)


@router.post("/apple/callback")
async def apple_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Apple Sign In callback (uses form_post response mode)."""
    form = await request.form()
    code = form.get("code")
    state = form.get("state")
    id_token = form.get("id_token")
    user_data = form.get("user")  # Only provided on first sign-in

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state"
        )

    # Validate state
    state_data = _sso_states.pop(state, None)
    if not state_data or state_data["provider"] != "apple":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state"
        )

    callback_url = f"{BACKEND_URL}/api/v1/sso/apple/callback"

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://appleid.apple.com/auth/token",
            data={
                "client_id": APPLE_CLIENT_ID,
                "client_secret": APPLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for tokens"
            )

        tokens = token_response.json()
        apple_id_token = tokens.get("id_token")

    # Decode ID token to get user info (simplified - in production use proper JWT validation)
    import base64
    import json

    try:
        payload_b64 = apple_id_token.split(".")[1]
        # Add padding if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        email = payload.get("email")
        apple_user_id = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode Apple ID token"
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Apple"
        )

    # Find or create user
    user = db.query(User).filter(User.email == email).first()

    full_name = None
    if user_data:
        try:
            user_info = json.loads(user_data)
            name = user_info.get("name", {})
            full_name = f"{name.get('firstName', '')} {name.get('lastName', '')}".strip()
        except Exception:
            pass

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password="",
            is_active=True,
            email_verified=True,
            sso_provider="apple",
            sso_provider_id=apple_user_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.sso_provider:
            user.sso_provider = "apple"
            user.sso_provider_id = apple_user_id
            db.commit()

    # Create JWT token
    jwt_token = create_access_token(user.id)

    # Redirect to frontend with token
    redirect_uri = state_data.get("redirect_uri") or f"{FRONTEND_URL}/sso/callback"
    return RedirectResponse(url=f"{redirect_uri}?token={jwt_token}")
