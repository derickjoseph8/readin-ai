"""
Zapier Integration Routes for ReadIn AI.

Provides REST Hook endpoints for Zapier integration:
- POST /zapier/subscribe - Create webhook subscription (REST Hooks)
- DELETE /zapier/subscribe/{id} - Remove webhook subscription
- GET /zapier/triggers/{trigger}/sample - Get sample data for trigger setup
- POST /zapier/actions/{action}/execute - Execute an action

Implements Zapier's REST Hook specification:
https://platform.zapier.com/docs/triggers#rest-hook-trigger
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from database import get_db
from models import User, Meeting, ZapierSubscription
from auth import get_current_user
from integrations.zapier import (
    ZapierTriggerService, TriggerType, get_trigger_sample,
    ZapierActionService, ActionType, get_action_sample, get_action_fields,
    ZapierAuthService, verify_zapier_request, is_zapier_configured
)

logger = logging.getLogger("routes.zapier")
router = APIRouter(prefix="/zapier", tags=["zapier"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class SubscribeRequest(BaseModel):
    """Request to create a webhook subscription."""
    target_url: str = Field(
        ...,
        description="The URL to send webhook payloads to"
    )
    trigger_type: str = Field(
        ...,
        description="Type of trigger: meeting_ended, action_item_created, summary_generated"
    )


class SubscriptionResponse(BaseModel):
    """Response after creating a subscription."""
    id: int
    trigger_type: str
    target_url: str
    is_active: bool
    created_at: datetime


class ActionExecuteRequest(BaseModel):
    """Request to execute an action."""
    input_data: Dict[str, Any] = Field(
        ...,
        description="Action input data"
    )


class ActionExecuteResponse(BaseModel):
    """Response from action execution."""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class TriggerSampleResponse(BaseModel):
    """Sample data for a trigger."""
    trigger_type: str
    samples: List[Dict[str, Any]]


class ActionFieldsResponse(BaseModel):
    """Field definitions for an action."""
    action_type: str
    input_fields: List[Dict[str, Any]]
    output_fields: List[Dict[str, Any]]
    sample: Dict[str, Any]


class MeetingOption(BaseModel):
    """Meeting option for dropdowns."""
    id: int
    label: str


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.get("/auth/test")
async def test_authentication(
    current_user: User = Depends(get_current_user),
):
    """
    Test authentication endpoint for Zapier.

    Zapier uses this to verify the user's API key/token is valid.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.full_name or current_user.email,
    }


# =============================================================================
# SUBSCRIPTION ENDPOINTS (REST Hooks)
# =============================================================================

@router.post("/subscribe", response_model=SubscriptionResponse)
async def create_subscription(
    request: SubscribeRequest,
    raw_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_hook_secret: Optional[str] = Header(None, alias="X-Hook-Secret"),
):
    """
    Create a webhook subscription (REST Hook).

    Zapier calls this when a user creates a trigger. The target_url
    is where ReadIn will send event payloads when the trigger fires.

    If X-Hook-Secret header is provided, it will be used to sign
    outgoing webhook payloads for verification.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    # Validate trigger type
    try:
        trigger_type = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {request.trigger_type}. "
                   f"Valid types: {[t.value for t in TriggerType]}"
        )

    # Validate URL format
    if not request.target_url.startswith(("https://", "http://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_url must be a valid HTTP(S) URL"
        )

    # Create subscription
    service = ZapierTriggerService(db)
    subscription = service.create_subscription(
        user_id=current_user.id,
        trigger_type=trigger_type,
        target_url=request.target_url,
        hook_secret=x_hook_secret,
    )

    logger.info(
        f"Created Zapier subscription {subscription.id} "
        f"for user {current_user.id}, trigger {trigger_type.value}"
    )

    # Return with X-Hook-Secret header if provided
    return SubscriptionResponse(
        id=subscription.id,
        trigger_type=subscription.trigger_type,
        target_url=subscription.target_url,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
    )


@router.delete("/subscribe/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a webhook subscription.

    Zapier calls this when a user disables or deletes their trigger.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    # Get subscription
    subscription = db.query(ZapierSubscription).filter(
        ZapierSubscription.id == subscription_id,
        ZapierSubscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    # Delete subscription
    service = ZapierTriggerService(db)
    service.delete_subscription(subscription_id)

    logger.info(
        f"Deleted Zapier subscription {subscription_id} "
        f"for user {current_user.id}"
    )

    return {"success": True, "message": "Subscription deleted"}


@router.get("/subscriptions")
async def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
):
    """
    List all webhook subscriptions for the current user.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    query = db.query(ZapierSubscription).filter(
        ZapierSubscription.user_id == current_user.id
    )

    if trigger_type:
        query = query.filter(ZapierSubscription.trigger_type == trigger_type)

    subscriptions = query.order_by(ZapierSubscription.created_at.desc()).all()

    return {
        "subscriptions": [
            {
                "id": sub.id,
                "trigger_type": sub.trigger_type,
                "target_url": sub.target_url,
                "is_active": sub.is_active,
                "last_triggered_at": sub.last_triggered_at,
                "consecutive_failures": sub.consecutive_failures,
                "created_at": sub.created_at,
            }
            for sub in subscriptions
        ]
    }


# =============================================================================
# TRIGGER ENDPOINTS
# =============================================================================

@router.get("/triggers/{trigger_type}/sample", response_model=TriggerSampleResponse)
async def get_trigger_sample_data(
    trigger_type: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get sample data for a trigger.

    Zapier uses this during zap setup to show users what fields
    will be available for mapping.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    try:
        trigger = TriggerType(trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid trigger type: {trigger_type}. "
                   f"Valid types: {[t.value for t in TriggerType]}"
        )

    samples = get_trigger_sample(trigger)

    return TriggerSampleResponse(
        trigger_type=trigger_type,
        samples=samples,
    )


@router.get("/triggers")
async def list_triggers(
    current_user: User = Depends(get_current_user),
):
    """
    List all available triggers.

    Returns metadata about each trigger for Zapier's integration setup.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    return {
        "triggers": [
            {
                "key": TriggerType.MEETING_ENDED.value,
                "label": "Meeting Ended",
                "description": "Triggers when a meeting session ends",
                "noun": "Meeting",
            },
            {
                "key": TriggerType.ACTION_ITEM_CREATED.value,
                "label": "Action Item Created",
                "description": "Triggers when a new action item is extracted from a meeting",
                "noun": "Action Item",
            },
            {
                "key": TriggerType.SUMMARY_GENERATED.value,
                "label": "Summary Generated",
                "description": "Triggers when a meeting summary is created",
                "noun": "Summary",
            },
        ]
    }


# =============================================================================
# ACTION ENDPOINTS
# =============================================================================

@router.post("/actions/{action_type}/execute", response_model=ActionExecuteResponse)
async def execute_action(
    action_type: str,
    request: ActionExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a Zapier action.

    Actions allow Zapier to create resources in ReadIn, such as
    action items or meeting notes.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    # Validate action type
    try:
        action = ActionType(action_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action type: {action_type}. "
                   f"Valid types: {[a.value for a in ActionType]}"
        )

    # Execute action
    service = ZapierActionService(db)
    try:
        result = service.execute_action(
            action_type=action,
            user_id=current_user.id,
            input_data=request.input_data,
        )

        logger.info(
            f"Executed Zapier action {action_type} "
            f"for user {current_user.id}"
        )

        return ActionExecuteResponse(
            success=True,
            data=result,
        )

    except ValueError as e:
        logger.warning(
            f"Zapier action {action_type} failed "
            f"for user {current_user.id}: {e}"
        )
        return ActionExecuteResponse(
            success=False,
            data={},
            error=str(e),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error in Zapier action {action_type} "
            f"for user {current_user.id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution failed: {str(e)}"
        )


@router.get("/actions/{action_type}/fields", response_model=ActionFieldsResponse)
async def get_action_field_definitions(
    action_type: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get field definitions for an action.

    Zapier uses this to display input fields during action setup.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    try:
        action = ActionType(action_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action type: {action_type}. "
                   f"Valid types: {[a.value for a in ActionType]}"
        )

    fields = get_action_fields(action)
    sample = get_action_sample(action)

    return ActionFieldsResponse(
        action_type=action_type,
        input_fields=fields.get("input_fields", []),
        output_fields=fields.get("output_fields", []),
        sample=sample,
    )


@router.get("/actions")
async def list_actions(
    current_user: User = Depends(get_current_user),
):
    """
    List all available actions.

    Returns metadata about each action for Zapier's integration setup.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    return {
        "actions": [
            {
                "key": ActionType.CREATE_ACTION_ITEM.value,
                "label": "Create Action Item",
                "description": "Create a new action item attached to a meeting",
                "noun": "Action Item",
            },
            {
                "key": ActionType.ADD_MEETING_NOTE.value,
                "label": "Add Meeting Note",
                "description": "Add a note to an existing meeting",
                "noun": "Meeting Note",
            },
        ]
    }


# =============================================================================
# DYNAMIC FIELD ENDPOINTS (for dropdowns)
# =============================================================================

@router.get("/meetings", response_model=List[MeetingOption])
async def get_meetings_for_dropdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get recent meetings for dropdown selection in Zapier.

    Used by actions that require a meeting_id field.
    """
    if not is_zapier_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zapier integration not configured"
        )

    service = ZapierActionService(db)
    meetings = service.get_meetings_for_action(current_user.id, limit)

    return [
        MeetingOption(id=m["id"], label=m["label"])
        for m in meetings
    ]


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/status")
async def get_zapier_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Zapier integration status for the current user.
    """
    is_configured = is_zapier_configured()

    if not is_configured:
        return {
            "is_configured": False,
            "is_connected": False,
            "subscription_count": 0,
            "active_triggers": [],
        }

    # Count subscriptions
    subscriptions = db.query(ZapierSubscription).filter(
        ZapierSubscription.user_id == current_user.id,
        ZapierSubscription.is_active == True
    ).all()

    active_triggers = list(set(sub.trigger_type for sub in subscriptions))

    return {
        "is_configured": True,
        "is_connected": len(subscriptions) > 0,
        "subscription_count": len(subscriptions),
        "active_triggers": active_triggers,
    }
