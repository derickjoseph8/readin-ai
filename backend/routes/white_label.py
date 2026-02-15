"""
White-Label Configuration API routes.

Provides endpoints for:
- Custom branding (logo, colors)
- Custom domain configuration
- Email branding
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from database import get_db
from models import User, Organization, WhiteLabelConfig, AuditLog
from auth import get_current_user

router = APIRouter(prefix="/white-label", tags=["White Label"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class WhiteLabelUpdate(BaseModel):
    """Update white-label configuration request."""
    # Branding
    company_name: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    favicon_url: Optional[HttpUrl] = None

    # Colors
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None

    # Custom domain
    custom_domain: Optional[str] = None

    # Email branding
    email_from_name: Optional[str] = None
    email_reply_to: Optional[str] = None
    email_footer_text: Optional[str] = None

    # Features
    hide_powered_by: Optional[bool] = None
    custom_terms_url: Optional[HttpUrl] = None
    custom_privacy_url: Optional[HttpUrl] = None
    custom_support_email: Optional[str] = None


class WhiteLabelResponse(BaseModel):
    """White-label configuration response."""
    id: int
    organization_id: int
    company_name: Optional[str]
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: str
    secondary_color: str
    background_color: str
    text_color: str
    custom_domain: Optional[str]
    domain_verified: bool
    email_from_name: Optional[str]
    email_reply_to: Optional[str]
    email_footer_text: Optional[str]
    hide_powered_by: bool
    custom_terms_url: Optional[str]
    custom_privacy_url: Optional[str]
    custom_support_email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DomainVerificationResponse(BaseModel):
    """Domain verification status response."""
    domain: str
    verified: bool
    verification_record: Optional[str]
    verification_type: str
    instructions: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_hex_color(color: str) -> bool:
    """Validate a hex color code."""
    if not color:
        return True
    if not color.startswith('#'):
        return False
    if len(color) != 7:
        return False
    try:
        int(color[1:], 16)
        return True
    except ValueError:
        return False


def get_or_create_config(user: User, db: Session) -> WhiteLabelConfig:
    """Get or create white-label config for user's organization."""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="White-label configuration is only available for organizations"
        )

    if user.role_in_org != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can manage white-label settings"
        )

    config = db.query(WhiteLabelConfig).filter(
        WhiteLabelConfig.organization_id == user.organization_id
    ).first()

    if not config:
        config = WhiteLabelConfig(organization_id=user.organization_id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return config


# =============================================================================
# WHITE-LABEL CONFIGURATION ENDPOINTS
# =============================================================================

@router.get("", response_model=WhiteLabelResponse)
def get_white_label_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get white-label configuration for the organization.

    Returns the current branding, colors, domain, and email settings.
    """
    config = get_or_create_config(user, db)

    return WhiteLabelResponse(
        id=config.id,
        organization_id=config.organization_id,
        company_name=config.company_name,
        logo_url=config.logo_url,
        favicon_url=config.favicon_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        background_color=config.background_color,
        text_color=config.text_color,
        custom_domain=config.custom_domain,
        domain_verified=config.domain_verified,
        email_from_name=config.email_from_name,
        email_reply_to=config.email_reply_to,
        email_footer_text=config.email_footer_text,
        hide_powered_by=config.hide_powered_by,
        custom_terms_url=config.custom_terms_url,
        custom_privacy_url=config.custom_privacy_url,
        custom_support_email=config.custom_support_email,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.put("", response_model=WhiteLabelResponse)
def update_white_label_config(
    request: WhiteLabelUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update white-label configuration.

    **Branding:**
    - `company_name`: Your company name to display
    - `logo_url`: URL to your logo (recommended: 200x50px)
    - `favicon_url`: URL to your favicon (recommended: 32x32px)

    **Colors (hex format):**
    - `primary_color`: Main accent color (default: #d4af37)
    - `secondary_color`: Secondary accent color (default: #10b981)
    - `background_color`: Background color (default: #0a0a0a)
    - `text_color`: Text color (default: #ffffff)

    **Custom Domain:**
    - `custom_domain`: Your custom domain (e.g., app.yourcompany.com)

    **Email Branding:**
    - `email_from_name`: Name to show in "From" field
    - `email_reply_to`: Reply-to email address
    - `email_footer_text`: Custom footer text for emails

    **Features:**
    - `hide_powered_by`: Hide "Powered by ReadIn AI" branding
    - `custom_terms_url`: URL to your terms of service
    - `custom_privacy_url`: URL to your privacy policy
    - `custom_support_email`: Your support email
    """
    config = get_or_create_config(user, db)

    # Validate colors
    colors = ['primary_color', 'secondary_color', 'background_color', 'text_color']
    for color_field in colors:
        color_value = getattr(request, color_field)
        if color_value and not validate_hex_color(color_value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {color_field}: must be a valid hex color (e.g., #d4af37)"
            )

    # Update fields
    update_data = request.dict(exclude_unset=True)

    # Convert HttpUrl to string
    for url_field in ['logo_url', 'favicon_url', 'custom_terms_url', 'custom_privacy_url']:
        if url_field in update_data and update_data[url_field]:
            update_data[url_field] = str(update_data[url_field])

    # If custom domain is being changed, reset verification
    if 'custom_domain' in update_data:
        if update_data['custom_domain'] != config.custom_domain:
            config.domain_verified = False

    for key, value in update_data.items():
        setattr(config, key, value)

    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="white_label_update",
        resource_type="WhiteLabelConfig",
        resource_id=config.id,
        details={"updated_fields": list(update_data.keys())}
    )
    db.add(audit)
    db.commit()

    return WhiteLabelResponse(
        id=config.id,
        organization_id=config.organization_id,
        company_name=config.company_name,
        logo_url=config.logo_url,
        favicon_url=config.favicon_url,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        background_color=config.background_color,
        text_color=config.text_color,
        custom_domain=config.custom_domain,
        domain_verified=config.domain_verified,
        email_from_name=config.email_from_name,
        email_reply_to=config.email_reply_to,
        email_footer_text=config.email_footer_text,
        hide_powered_by=config.hide_powered_by,
        custom_terms_url=config.custom_terms_url,
        custom_privacy_url=config.custom_privacy_url,
        custom_support_email=config.custom_support_email,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


# =============================================================================
# DOMAIN VERIFICATION
# =============================================================================

@router.get("/domain/verify", response_model=DomainVerificationResponse)
def get_domain_verification(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get domain verification instructions.

    Returns the DNS record that needs to be added to verify domain ownership.
    """
    config = get_or_create_config(user, db)

    if not config.custom_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No custom domain configured"
        )

    # Generate verification token (in production, this would be stored and validated)
    import hashlib
    verification_token = hashlib.sha256(
        f"{config.organization_id}:{config.custom_domain}".encode()
    ).hexdigest()[:32]

    return DomainVerificationResponse(
        domain=config.custom_domain,
        verified=config.domain_verified,
        verification_record=f"readin-verify={verification_token}",
        verification_type="TXT",
        instructions=(
            f"Add a TXT record to your DNS:\n\n"
            f"Host: _readin-verify.{config.custom_domain}\n"
            f"Type: TXT\n"
            f"Value: readin-verify={verification_token}\n\n"
            f"After adding the record, click 'Verify Domain' to complete verification. "
            f"DNS changes may take up to 48 hours to propagate."
        )
    )


@router.post("/domain/verify")
def verify_domain(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify custom domain ownership.

    Checks for the required DNS TXT record.
    """
    config = get_or_create_config(user, db)

    if not config.custom_domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No custom domain configured"
        )

    if config.domain_verified:
        return {
            "status": "success",
            "message": "Domain already verified",
            "domain": config.custom_domain
        }

    # In a real implementation, this would:
    # 1. Query DNS for the TXT record
    # 2. Validate the verification token
    # 3. Set up SSL certificate provisioning

    # For demonstration, we'll simulate verification
    # In production, use dnspython to check DNS:
    # import dns.resolver
    # answers = dns.resolver.resolve(f'_readin-verify.{config.custom_domain}', 'TXT')

    return {
        "status": "pending",
        "message": "Domain verification initiated. Please ensure the DNS record is configured correctly.",
        "domain": config.custom_domain,
        "note": "In production, this endpoint would verify the actual DNS record."
    }


# =============================================================================
# PREVIEW ENDPOINTS
# =============================================================================

@router.get("/preview")
def get_preview_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get white-label configuration for preview/rendering.

    Returns a simplified config object suitable for frontend rendering.
    """
    config = get_or_create_config(user, db)

    return {
        "branding": {
            "company_name": config.company_name or "ReadIn AI",
            "logo_url": config.logo_url,
            "favicon_url": config.favicon_url,
        },
        "colors": {
            "primary": config.primary_color,
            "secondary": config.secondary_color,
            "background": config.background_color,
            "text": config.text_color,
        },
        "features": {
            "hide_powered_by": config.hide_powered_by,
            "terms_url": config.custom_terms_url or "/terms",
            "privacy_url": config.custom_privacy_url or "/privacy",
            "support_email": config.custom_support_email or "support@getreadin.ai",
        }
    }


@router.post("/reset")
def reset_white_label_config(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset white-label configuration to defaults.

    This removes all custom branding and resets colors to default values.
    """
    config = get_or_create_config(user, db)

    # Reset to defaults
    config.company_name = None
    config.logo_url = None
    config.favicon_url = None
    config.primary_color = "#d4af37"
    config.secondary_color = "#10b981"
    config.background_color = "#0a0a0a"
    config.text_color = "#ffffff"
    config.custom_domain = None
    config.domain_verified = False
    config.email_from_name = None
    config.email_reply_to = None
    config.email_footer_text = None
    config.hide_powered_by = False
    config.custom_terms_url = None
    config.custom_privacy_url = None
    config.custom_support_email = None
    config.updated_at = datetime.utcnow()

    db.commit()

    return {"status": "success", "message": "White-label configuration reset to defaults"}
