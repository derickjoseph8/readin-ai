"""
Two-Factor Authentication (TOTP) routes.

Supports authenticator apps like:
- Google Authenticator
- Microsoft Authenticator
- Duo Mobile
- Authy
- 1Password
"""

import secrets
import base64
from io import BytesIO
from typing import List, Optional
from datetime import datetime

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User
from auth import get_current_user, verify_password, hash_password

router = APIRouter(prefix="/api/v1/2fa", tags=["Two-Factor Authentication"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TwoFactorSetupResponse(BaseModel):
    """Response when setting up 2FA."""
    secret: str
    qr_code: str  # Base64 encoded QR code image
    provisioning_uri: str


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify TOTP code."""
    code: str


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA."""
    password: str
    code: Optional[str] = None  # Either TOTP code or backup code


class TwoFactorStatusResponse(BaseModel):
    """2FA status for current user."""
    enabled: bool
    backup_codes_remaining: int


class BackupCodesResponse(BaseModel):
    """Response with backup codes."""
    codes: List[str]


class TwoFactorLoginRequest(BaseModel):
    """Request for 2FA login verification."""
    code: str
    is_backup_code: bool = False


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_backup_codes(count: int = 10) -> tuple[List[str], List[str]]:
    """
    Generate a list of backup codes.

    Returns a tuple of (plain_codes, hashed_codes).
    Plain codes are shown to the user once, hashed codes are stored in the database.
    """
    plain_codes = []
    hashed_codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric codes
        code = secrets.token_hex(4).upper()
        plain_codes.append(code)
        hashed_codes.append(hash_password(code))
    return plain_codes, hashed_codes


def generate_qr_code(provisioning_uri: str) -> str:
    """Generate a QR code image and return as base64."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status", response_model=TwoFactorStatusResponse)
def get_2fa_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current 2FA status for the authenticated user.
    """
    backup_codes = user.totp_backup_codes or []
    # Count unused backup codes (non-empty strings)
    unused_codes = [c for c in backup_codes if c]

    return TwoFactorStatusResponse(
        enabled=user.totp_enabled or False,
        backup_codes_remaining=len(unused_codes)
    )


@router.post("/setup", response_model=TwoFactorSetupResponse)
def setup_2fa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize 2FA setup. Returns secret and QR code.
    User must verify with a code before 2FA is enabled.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )

    # Generate a new TOTP secret
    secret = pyotp.random_base32()

    # Store the secret (not enabled yet until verified)
    user.totp_secret = secret
    db.commit()

    # Create the provisioning URI for authenticator apps
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="ReadIn AI"
    )

    # Generate QR code
    qr_code = generate_qr_code(provisioning_uri)

    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=qr_code,
        provisioning_uri=provisioning_uri
    )


@router.post("/verify")
def verify_and_enable_2fa(
    request: TwoFactorVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify TOTP code and enable 2FA.
    Must be called after /setup with a valid code from the authenticator app.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please initiate 2FA setup first"
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(request.code, valid_window=0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Generate backup codes (plain for display, hashed for storage)
    plain_codes, hashed_codes = generate_backup_codes(10)

    # Enable 2FA
    user.totp_enabled = True
    user.totp_backup_codes = hashed_codes
    db.commit()

    return {
        "message": "Two-factor authentication enabled successfully",
        "backup_codes": plain_codes
    }


@router.post("/disable")
def disable_2fa(
    request: TwoFactorDisableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA. Requires password and either TOTP code or backup code.
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )

    # Verify TOTP code if provided
    if request.code:
        totp = pyotp.TOTP(user.totp_secret)
        code_valid = totp.verify(request.code, valid_window=0)

        # Check backup codes if TOTP didn't match
        if not code_valid:
            backup_codes = user.totp_backup_codes or []
            code_upper = request.code.upper().replace("-", "")
            # Check each hashed backup code
            for hashed_code in backup_codes:
                if verify_password(code_upper, hashed_code):
                    code_valid = True
                    break

        if not code_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

    # Disable 2FA
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_backup_codes = []
    db.commit()

    return {"message": "Two-factor authentication disabled successfully"}


@router.post("/backup-codes/regenerate", response_model=BackupCodesResponse)
def regenerate_backup_codes(
    request: TwoFactorVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate backup codes. Requires current TOTP code.
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(request.code, valid_window=0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Generate new backup codes (plain for display, hashed for storage)
    plain_codes, hashed_codes = generate_backup_codes(10)
    user.totp_backup_codes = hashed_codes
    db.commit()

    return BackupCodesResponse(codes=plain_codes)


@router.post("/validate")
def validate_totp_code(
    request: TwoFactorLoginRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate a TOTP code or backup code.
    Used during login when 2FA is enabled.
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )

    if request.is_backup_code:
        # Validate backup code (hashed with bcrypt)
        backup_codes = user.totp_backup_codes or []
        code_upper = request.code.upper().replace("-", "")

        # Find and verify the matching hashed backup code
        matched_index = None
        for i, hashed_code in enumerate(backup_codes):
            if verify_password(code_upper, hashed_code):
                matched_index = i
                break

        if matched_index is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid backup code"
            )

        # Remove used backup code
        backup_codes.pop(matched_index)
        user.totp_backup_codes = backup_codes
        db.commit()

        return {
            "valid": True,
            "message": "Backup code verified",
            "backup_codes_remaining": len(backup_codes)
        }
    else:
        # Validate TOTP code
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(request.code, valid_window=0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        return {
            "valid": True,
            "message": "Code verified successfully"
        }


# =============================================================================
# PUBLIC ENDPOINT FOR LOGIN FLOW
# =============================================================================

@router.post("/check-required")
def check_2fa_required(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Check if 2FA is required for a user (by email).
    Used before login to determine if 2FA step is needed.
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Don't reveal if user exists
        return {"requires_2fa": False}

    return {"requires_2fa": user.totp_enabled or False}
