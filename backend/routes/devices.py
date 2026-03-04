"""
Device token management routes for push notifications.

Provides endpoints for registering, updating, and removing device tokens
used with Firebase Cloud Messaging for push notifications.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from database import get_db
from models import User, DeviceToken
from auth import get_current_user

router = APIRouter(prefix="/devices", tags=["Devices"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class DeviceTokenRegisterRequest(BaseModel):
    """Request to register a device token for push notifications."""
    token: str = Field(..., min_length=10, max_length=500, description="FCM device registration token")
    platform: str = Field(..., pattern="^(ios|android|web|desktop)$", description="Device platform")
    device_name: Optional[str] = Field(None, max_length=255, description="Human-readable device name")
    device_id: Optional[str] = Field(None, max_length=255, description="Unique device identifier")
    app_version: Optional[str] = Field(None, max_length=50, description="App version")
    os_version: Optional[str] = Field(None, max_length=50, description="Operating system version")


class DeviceTokenUpdateRequest(BaseModel):
    """Request to update a device token."""
    token: Optional[str] = Field(None, min_length=10, max_length=500, description="New FCM token")
    device_name: Optional[str] = Field(None, max_length=255)
    app_version: Optional[str] = Field(None, max_length=50)
    os_version: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class DeviceTokenResponse(BaseModel):
    """Response model for a device token."""
    id: int
    platform: str
    device_name: Optional[str]
    device_id: Optional[str]
    app_version: Optional[str]
    os_version: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class DeviceTokenListResponse(BaseModel):
    """Response model for list of device tokens."""
    devices: List[DeviceTokenResponse]
    total: int


class PushNotificationStatusResponse(BaseModel):
    """Response model for push notification status."""
    firebase_configured: bool
    total_devices: int
    active_devices: int
    platforms: dict


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/register", response_model=DeviceTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_device_token(
    request: DeviceTokenRegisterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a device token for push notifications.

    If a token already exists for this user, it will be updated instead.
    If the same token exists for a different user, the ownership will be transferred.
    """
    # Check if token already exists
    existing_token = db.query(DeviceToken).filter(
        DeviceToken.token == request.token
    ).first()

    if existing_token:
        # Token exists - transfer ownership to current user if different
        if existing_token.user_id != user.id:
            existing_token.user_id = user.id

        # Update device info
        existing_token.platform = request.platform
        existing_token.device_name = request.device_name
        existing_token.device_id = request.device_id
        existing_token.app_version = request.app_version
        existing_token.os_version = request.os_version
        existing_token.is_active = True
        existing_token.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(existing_token)
        return existing_token

    # Create new device token
    device_token = DeviceToken(
        user_id=user.id,
        token=request.token,
        platform=request.platform,
        device_name=request.device_name,
        device_id=request.device_id,
        app_version=request.app_version,
        os_version=request.os_version,
    )

    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    return device_token


@router.get("/", response_model=DeviceTokenListResponse)
async def list_device_tokens(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all registered device tokens for the current user.
    """
    devices = db.query(DeviceToken).filter(
        DeviceToken.user_id == user.id
    ).order_by(DeviceToken.created_at.desc()).all()

    return DeviceTokenListResponse(
        devices=devices,
        total=len(devices)
    )


@router.get("/status", response_model=PushNotificationStatusResponse)
async def get_push_notification_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get push notification status for the current user.

    Returns Firebase configuration status and device statistics.
    """
    from services.notification_service import is_firebase_configured

    devices = db.query(DeviceToken).filter(
        DeviceToken.user_id == user.id
    ).all()

    # Count devices by platform
    platforms = {}
    active_count = 0
    for device in devices:
        if device.platform not in platforms:
            platforms[device.platform] = {"total": 0, "active": 0}
        platforms[device.platform]["total"] += 1
        if device.is_active:
            platforms[device.platform]["active"] += 1
            active_count += 1

    return PushNotificationStatusResponse(
        firebase_configured=is_firebase_configured(),
        total_devices=len(devices),
        active_devices=active_count,
        platforms=platforms
    )


@router.get("/{device_id}", response_model=DeviceTokenResponse)
async def get_device_token(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific device token.
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.id == device_id,
        DeviceToken.user_id == user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    return device


@router.patch("/{device_id}", response_model=DeviceTokenResponse)
async def update_device_token(
    device_id: int,
    request: DeviceTokenUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a device token's information.
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.id == device_id,
        DeviceToken.user_id == user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    # Update fields if provided
    if request.token is not None:
        # Check if new token is already in use by another device
        existing = db.query(DeviceToken).filter(
            DeviceToken.token == request.token,
            DeviceToken.id != device_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This token is already registered to another device"
            )
        device.token = request.token

    if request.device_name is not None:
        device.device_name = request.device_name
    if request.app_version is not None:
        device.app_version = request.app_version
    if request.os_version is not None:
        device.os_version = request.os_version
    if request.is_active is not None:
        device.is_active = request.is_active

    device.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(device)

    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_token(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a device token (unregister from push notifications).
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.id == device_id,
        DeviceToken.user_id == user.id
    ).first()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    db.delete(device)
    db.commit()

    return None


@router.post("/unregister", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_by_token(
    request: DeviceTokenRegisterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unregister a device using its FCM token.

    Useful when the device ID is not known but the FCM token is available.
    """
    device = db.query(DeviceToken).filter(
        DeviceToken.token == request.token,
        DeviceToken.user_id == user.id
    ).first()

    if device:
        db.delete(device)
        db.commit()

    # Return success even if token not found (idempotent)
    return None


@router.post("/deactivate-all", status_code=status.HTTP_200_OK)
async def deactivate_all_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate all device tokens for the current user.

    This stops push notifications without deleting the device records.
    Useful for temporarily disabling notifications.
    """
    count = db.query(DeviceToken).filter(
        DeviceToken.user_id == user.id,
        DeviceToken.is_active == True
    ).update({"is_active": False, "updated_at": datetime.utcnow()})

    db.commit()

    return {"deactivated_count": count}


@router.post("/activate-all", status_code=status.HTTP_200_OK)
async def activate_all_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate all device tokens for the current user.

    Re-enables push notifications for all registered devices.
    """
    count = db.query(DeviceToken).filter(
        DeviceToken.user_id == user.id,
        DeviceToken.is_active == False
    ).update({"is_active": True, "updated_at": datetime.utcnow()})

    db.commit()

    return {"activated_count": count}
