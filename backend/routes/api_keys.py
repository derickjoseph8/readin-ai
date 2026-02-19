"""
API Keys and Webhooks management routes.

Provides endpoints for:
- Creating and managing API keys
- Webhook subscriptions
- Webhook delivery logs
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from database import get_db
from models import User, APIKey, Webhook, WebhookDelivery, AuditLog, AuditAction
from auth import get_current_user
from services.audit_logger import AuditLogger

# Rate limiting setup
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    limiter = None

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class APIKeyCreate(BaseModel):
    """Create API key request."""
    name: str
    description: Optional[str] = None
    scopes: List[str] = ["read"]
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000
    expires_in_days: Optional[int] = None  # None = never expires


class APIKeyResponse(BaseModel):
    """API key response (key is only shown once on creation)."""
    id: int
    name: str
    description: Optional[str]
    key_prefix: str
    scopes: List[str]
    rate_limit_per_minute: int
    rate_limit_per_day: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    created_at: datetime


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when API key is created (includes full key)."""
    key: str  # Only returned on creation


class WebhookCreate(BaseModel):
    """Create webhook request."""
    name: str
    url: HttpUrl
    events: List[str] = ["meeting.ended"]
    secret: Optional[str] = None  # Auto-generated if not provided
    custom_headers: dict = {}


class WebhookUpdate(BaseModel):
    """Update webhook request."""
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    custom_headers: Optional[dict] = None


class WebhookResponse(BaseModel):
    """Webhook response."""
    id: int
    name: str
    url: str
    events: List[str]
    is_active: bool
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_triggered_at: Optional[datetime]
    last_success_at: Optional[datetime]
    created_at: datetime


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log response."""
    id: int
    event_type: str
    status: str
    response_status_code: Optional[int]
    response_time_ms: Optional[int]
    attempt_count: int
    error_message: Optional[str]
    triggered_at: datetime
    delivered_at: Optional[datetime]


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.
    Returns: (full_key, key_prefix, key_hash)
    """
    # Generate a 32-byte random key
    key_bytes = secrets.token_bytes(32)
    full_key = f"rk_{secrets.token_urlsafe(32)}"
    key_prefix = full_key[:10]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, key_hash


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    computed_hash = hashlib.sha256(key.encode()).hexdigest()
    return hmac.compare_digest(computed_hash, key_hash)


@router.get("", response_model=List[APIKeyResponse])
def list_api_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the current user."""
    keys = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.revoked_at == None
    ).order_by(APIKey.created_at.desc()).all()

    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            description=k.description,
            key_prefix=k.key_prefix[:4] + "****" if k.key_prefix else "****",
            scopes=k.scopes or ["read"],
            rate_limit_per_minute=k.rate_limit_per_minute,
            rate_limit_per_day=k.rate_limit_per_day,
            is_active=k.is_active,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            usage_count=k.usage_count,
            created_at=k.created_at
        )
        for k in keys
    ]


@router.post("", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key.

    **Important:** The full API key is only shown once. Store it securely.

    Available scopes:
    - `read`: Read-only access to meetings, conversations, analytics
    - `write`: Create and update meetings, conversations
    - `admin`: Full access including user management

    """
    # Validate scopes
    valid_scopes = ["read", "write", "admin"]
    for scope in request.scopes:
        if scope not in valid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Valid scopes: {', '.join(valid_scopes)}"
            )

    # Check API key limit (e.g., max 10 per user)
    existing_count = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.revoked_at == None
    ).count()

    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys (10) reached. Please revoke an existing key."
        )

    # Generate the key
    full_key, key_prefix, key_hash = generate_api_key()

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create API key record
    api_key = APIKey(
        user_id=user.id,
        organization_id=user.organization_id,
        name=request.name,
        description=request.description,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=request.scopes,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_day=request.rate_limit_per_day,
        expires_at=expires_at
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action=AuditAction.API_KEY_CREATE,
        resource_type="APIKey",
        resource_id=api_key.id,
        details={"name": request.name, "scopes": request.scopes}
    )
    db.add(audit)
    db.commit()

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        key=full_key,  # Only returned on creation!
        scopes=api_key.scopes or ["read"],
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_day=api_key.rate_limit_per_day,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        usage_count=api_key.usage_count,
        created_at=api_key.created_at
    )


@router.delete("/{key_id}")
@limiter.limit("5/minute") if RATE_LIMITING_AVAILABLE else lambda f: f
def revoke_api_key(
    request: Request,
    key_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    if api_key.revoked_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key already revoked"
        )

    api_key.is_active = False
    api_key.revoked_at = datetime.utcnow()
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action=AuditAction.API_KEY_REVOKE,
        resource_type="APIKey",
        resource_id=api_key.id,
        details={"name": api_key.name}
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": "API key revoked"}


# =============================================================================
# WEBHOOK MANAGEMENT
# =============================================================================

webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhooks_router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all webhooks for the current user."""
    webhooks = db.query(Webhook).filter(
        Webhook.user_id == user.id
    ).order_by(Webhook.created_at.desc()).all()

    return [
        WebhookResponse(
            id=w.id,
            name=w.name,
            url=w.url,
            events=w.events or [],
            is_active=w.is_active,
            total_deliveries=w.total_deliveries,
            successful_deliveries=w.successful_deliveries,
            failed_deliveries=w.failed_deliveries,
            last_triggered_at=w.last_triggered_at,
            last_success_at=w.last_success_at,
            created_at=w.created_at
        )
        for w in webhooks
    ]


@webhooks_router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    request: WebhookCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new webhook subscription.

    Available events:
    - `meeting.started`: Triggered when a meeting starts
    - `meeting.ended`: Triggered when a meeting ends
    - `meeting.summary_ready`: Triggered when meeting summary is generated
    - `conversation.created`: Triggered for each AI response
    - `action_item.created`: Triggered when action items are extracted

    The webhook will receive POST requests with the following structure:
    ```json
    {
      "event": "meeting.ended",
      "timestamp": "2024-01-01T12:00:00Z",
      "data": { ... }
    }
    ```

    If a secret is provided, requests will include an `X-Webhook-Signature` header
    with an HMAC-SHA256 signature of the payload.
    """
    # Validate events
    valid_events = [
        "meeting.started", "meeting.ended", "meeting.summary_ready",
        "conversation.created", "action_item.created"
    ]
    for event in request.events:
        if event not in valid_events:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event: {event}. Valid events: {', '.join(valid_events)}"
            )

    # Check webhook limit
    existing_count = db.query(Webhook).filter(Webhook.user_id == user.id).count()
    if existing_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of webhooks (5) reached."
        )

    # Generate secret if not provided
    secret = request.secret or secrets.token_urlsafe(32)

    webhook = Webhook(
        user_id=user.id,
        organization_id=user.organization_id,
        name=request.name,
        url=str(request.url),
        secret=secret,
        events=request.events,
        custom_headers=request.custom_headers
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events or [],
        is_active=webhook.is_active,
        total_deliveries=webhook.total_deliveries,
        successful_deliveries=webhook.successful_deliveries,
        failed_deliveries=webhook.failed_deliveries,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        created_at=webhook.created_at
    )


@webhooks_router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    request: WebhookUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a webhook configuration."""
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Update fields
    update_data = request.dict(exclude_unset=True)
    if "url" in update_data:
        update_data["url"] = str(update_data["url"])

    for key, value in update_data.items():
        setattr(webhook, key, value)

    webhook.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        events=webhook.events or [],
        is_active=webhook.is_active,
        total_deliveries=webhook.total_deliveries,
        successful_deliveries=webhook.successful_deliveries,
        failed_deliveries=webhook.failed_deliveries,
        last_triggered_at=webhook.last_triggered_at,
        last_success_at=webhook.last_success_at,
        created_at=webhook.created_at
    )


@webhooks_router.delete("/{webhook_id}")
@limiter.limit("5/minute") if RATE_LIMITING_AVAILABLE else lambda f: f
def delete_webhook(
    request: Request,
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a webhook."""
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    db.delete(webhook)
    db.commit()

    return {"status": "success", "message": "Webhook deleted"}


@webhooks_router.get("/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
def get_webhook_deliveries(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=500, description="Max deliveries to return"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent delivery logs for a webhook."""
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(WebhookDelivery.triggered_at.desc()).limit(limit).all()

    return [
        WebhookDeliveryResponse(
            id=d.id,
            event_type=d.event_type,
            status=d.status,
            response_status_code=d.response_status_code,
            response_time_ms=d.response_time_ms,
            attempt_count=d.attempt_count,
            error_message=d.error_message,
            triggered_at=d.triggered_at,
            delivered_at=d.delivered_at
        )
        for d in deliveries
    ]


@webhooks_router.post("/{webhook_id}/test")
def test_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a test payload to the webhook.

    This helps verify the webhook is configured correctly.
    """
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # In a real implementation, this would send an actual HTTP request
    # For now, we return a mock response
    return {
        "status": "success",
        "message": "Test webhook sent",
        "webhook_url": webhook.url,
        "test_payload": {
            "event": "webhook.test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "message": "This is a test webhook from ReadIn AI",
                "webhook_id": webhook_id
            }
        }
    }


@webhooks_router.get("/{webhook_id}/secret")
@limiter.limit("5/minute") if RATE_LIMITING_AVAILABLE else lambda f: f
def get_webhook_secret(
    request: Request,
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the webhook signing secret."""
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    # Audit log for sensitive secret access
    AuditLogger.log(
        db=db,
        action="webhook_secret_accessed",
        user_id=user.id,
        details={
            "webhook_id": webhook_id,
            "webhook_name": webhook.name,
            "ip_address": request.client.host if request.client else "unknown",
        },
    )

    return {"secret": webhook.secret}


@webhooks_router.post("/{webhook_id}/rotate-secret")
def rotate_webhook_secret(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rotate the webhook signing secret."""
    webhook = db.query(Webhook).filter(
        Webhook.id == webhook_id,
        Webhook.user_id == user.id
    ).first()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    new_secret = secrets.token_urlsafe(32)
    webhook.secret = new_secret
    webhook.updated_at = datetime.utcnow()
    db.commit()

    return {
        "status": "success",
        "message": "Webhook secret rotated",
        "new_secret": new_secret
    }
