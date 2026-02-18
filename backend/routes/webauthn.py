"""
WebAuthn/FIDO2 routes for hardware key authentication.

Endpoints:
- POST /api/v1/auth/webauthn/register/begin - Start registration ceremony
- POST /api/v1/auth/webauthn/register/complete - Complete registration
- POST /api/v1/auth/webauthn/authenticate/begin - Start authentication ceremony
- POST /api/v1/auth/webauthn/authenticate/complete - Complete authentication
- GET /api/v1/auth/webauthn/credentials - List user's registered credentials
- DELETE /api/v1/auth/webauthn/credentials/{id} - Remove a credential
- PATCH /api/v1/auth/webauthn/credentials/{id} - Rename a credential
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
try:
    from webauthn.helpers.base64url import base64url_to_bytes, bytes_to_base64url
except ImportError:
    # Fallback for different py_webauthn versions
    import base64
    def base64url_to_bytes(val: str) -> bytes:
        padding = 4 - len(val) % 4
        if padding != 4:
            val += '=' * padding
        return base64.urlsafe_b64decode(val)
    def bytes_to_base64url(val: bytes) -> str:
        return base64.urlsafe_b64encode(val).rstrip(b'=').decode('utf-8')

from database import get_db
from models import User, WebAuthnCredential
from auth import get_current_user, create_access_token
from services.webauthn_service import WebAuthnService, ChallengeStore
from middleware.rate_limiter import limiter


router = APIRouter(
    prefix="/api/v1/auth/webauthn",
    tags=["WebAuthn/FIDO2"]
)


# =============================================================================
# SCHEMAS
# =============================================================================

class RegistrationBeginResponse(BaseModel):
    """Response for registration begin endpoint."""
    options: dict  # PublicKeyCredentialCreationOptions
    challenge_id: str


class RegistrationCompleteRequest(BaseModel):
    """Request to complete registration."""
    challenge_id: str
    credential: dict  # PublicKeyCredential from navigator.credentials.create()
    device_name: Optional[str] = Field(None, max_length=100)


class RegistrationCompleteResponse(BaseModel):
    """Response after successful registration."""
    credential_id: int
    device_name: str
    created_at: datetime


class AuthenticationBeginRequest(BaseModel):
    """Request to begin authentication."""
    email: str


class AuthenticationBeginResponse(BaseModel):
    """Response for authentication begin endpoint."""
    options: dict  # PublicKeyCredentialRequestOptions
    challenge_id: str


class AuthenticationCompleteRequest(BaseModel):
    """Request to complete authentication."""
    challenge_id: str
    credential: dict  # PublicKeyCredential from navigator.credentials.get()


class AuthenticationCompleteResponse(BaseModel):
    """Response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str


class CredentialResponse(BaseModel):
    """Response for a single WebAuthn credential."""
    id: int
    device_name: str
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class CredentialRenameRequest(BaseModel):
    """Request to rename a credential."""
    device_name: str = Field(..., min_length=1, max_length=100)


# =============================================================================
# REGISTRATION ENDPOINTS
# =============================================================================

@router.post("/register/begin", response_model=RegistrationBeginResponse)
def register_begin(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Begin WebAuthn registration ceremony.

    Returns options that should be passed to navigator.credentials.create().
    The user must be authenticated to register a new credential.
    """
    service = WebAuthnService(db)

    # Get existing credentials to exclude
    existing_credentials = service.get_user_credentials(user.id)
    exclude_creds = [
        base64url_to_bytes(cred.credential_id)
        for cred in existing_credentials
    ]

    # Generate registration options
    options, challenge = service.generate_registration_challenge(
        user_id=user.id,
        user_email=user.email,
        user_name=user.full_name,
        exclude_credentials=exclude_creds
    )

    # Store challenge for verification
    import secrets
    challenge_id = secrets.token_urlsafe(32)
    ChallengeStore.store_challenge(f"reg:{user.id}:{challenge_id}", challenge)

    return RegistrationBeginResponse(
        options=options,
        challenge_id=challenge_id
    )


@router.post("/register/complete", response_model=RegistrationCompleteResponse)
def register_complete(
    request: Request,
    data: RegistrationCompleteRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete WebAuthn registration ceremony.

    Receives the credential from navigator.credentials.create() and
    verifies it against the stored challenge.
    """
    service = WebAuthnService(db)

    # Retrieve and validate challenge
    challenge = ChallengeStore.get_challenge(f"reg:{user.id}:{data.challenge_id}")
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration challenge"
        )

    try:
        # Verify the registration response
        credential_id, public_key, sign_count = service.verify_registration_credential(
            credential_response=data.credential,
            expected_challenge=challenge,
            user_id=user.id
        )

        # Save the credential
        credential = service.save_credential(
            user_id=user.id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            device_name=data.device_name
        )

        return RegistrationCompleteResponse(
            credential_id=credential.id,
            device_name=credential.device_name,
            created_at=credential.created_at
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {str(e)}"
        )


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/authenticate/begin", response_model=AuthenticationBeginResponse)
@limiter.limit("10/minute")
def authenticate_begin(
    request: Request,
    data: AuthenticationBeginRequest,
    db: Session = Depends(get_db)
):
    """
    Begin WebAuthn authentication ceremony.

    Returns options that should be passed to navigator.credentials.get().
    This endpoint is public (no authentication required).
    """
    # Look up user by email
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        # Don't reveal if user exists - return empty challenge
        # This allows the client to fail gracefully
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No security keys registered for this account"
        )

    service = WebAuthnService(db)

    # Get user's credentials
    credentials = service.get_user_credentials(user.id)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No security keys registered for this account"
        )

    # Get credential IDs
    allowed_creds = [
        base64url_to_bytes(cred.credential_id)
        for cred in credentials
    ]

    # Generate authentication options
    options, challenge = service.generate_authentication_challenge(
        allowed_credentials=allowed_creds
    )

    # Store challenge for verification
    import secrets
    challenge_id = secrets.token_urlsafe(32)
    ChallengeStore.store_challenge(f"auth:{user.id}:{challenge_id}", challenge)

    return AuthenticationBeginResponse(
        options=options,
        challenge_id=challenge_id
    )


@router.post("/authenticate/complete", response_model=AuthenticationCompleteResponse)
@limiter.limit("10/minute")
def authenticate_complete(
    request: Request,
    data: AuthenticationCompleteRequest,
    db: Session = Depends(get_db)
):
    """
    Complete WebAuthn authentication ceremony.

    Receives the credential from navigator.credentials.get() and
    verifies it against the stored challenge. Returns an access token
    on successful authentication.
    """
    service = WebAuthnService(db)

    # Find the credential by ID
    credential_id_bytes = base64url_to_bytes(data.credential['id'])
    stored_credential = service.get_credential_by_id(credential_id_bytes)

    if not stored_credential:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown security key"
        )

    # Get the user
    user = db.query(User).filter(User.id == stored_credential.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Retrieve and validate challenge
    challenge = ChallengeStore.get_challenge(f"auth:{user.id}:{data.challenge_id}")
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authentication challenge"
        )

    try:
        # Verify the authentication response
        new_sign_count = service.verify_authentication_credential(
            credential_response=data.credential,
            expected_challenge=challenge,
            credential_public_key=base64url_to_bytes(stored_credential.public_key),
            credential_current_sign_count=stored_credential.sign_count,
            credential_id=credential_id_bytes
        )

        # Update sign count
        service.update_sign_count(credential_id_bytes, new_sign_count)

        # Update user's last login
        user.last_login = datetime.utcnow()
        db.commit()

        # Generate access token
        access_token = create_access_token(user.id)

        return AuthenticationCompleteResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            email=user.email
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication verification failed: {str(e)}"
        )


# =============================================================================
# CREDENTIAL MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/credentials", response_model=List[CredentialResponse])
def list_credentials(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all WebAuthn credentials for the current user.
    """
    service = WebAuthnService(db)
    credentials = service.get_user_credentials(user.id)

    return [
        CredentialResponse(
            id=cred.id,
            device_name=cred.device_name,
            created_at=cred.created_at,
            last_used_at=cred.last_used_at
        )
        for cred in credentials
    ]


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a WebAuthn credential.

    Note: Users should always have at least one authentication method
    (password or security key) to avoid being locked out.
    """
    service = WebAuthnService(db)
    success = service.delete_credential(credential_id, user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    return {"message": "Security key removed successfully"}


@router.patch("/credentials/{credential_id}")
def rename_credential(
    credential_id: int,
    data: CredentialRenameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rename a WebAuthn credential.
    """
    service = WebAuthnService(db)
    success = service.rename_credential(credential_id, user.id, data.device_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )

    return {"message": "Security key renamed successfully", "device_name": data.device_name}


@router.get("/check-available")
def check_webauthn_available(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if a user has WebAuthn credentials registered.

    This is a public endpoint used to determine if the WebAuthn
    authentication option should be shown on the login page.
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Don't reveal if user exists
        return {"available": False}

    service = WebAuthnService(db)
    credentials = service.get_user_credentials(user.id)

    return {"available": len(credentials) > 0}
