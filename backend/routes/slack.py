"""
Slack webhook routes for ReadIn AI.

Provides endpoints for:
- POST /slack/events - Handle Slack events (messages, app_home, etc.)
- POST /slack/commands - Handle slash commands (/readin)
- POST /slack/interactions - Handle button clicks and other interactions

These routes integrate with slack-bolt through the FastAPI adapter.
"""

import logging
import json
import hmac
import hashlib
import time
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from config import SLACK_SIGNING_SECRET
from integrations.slack_app import (
    get_slack_app,
    is_slack_app_configured,
    create_slack_handler,
    SlackDailyDigest,
    send_meeting_summary_notification,
    send_action_item_reminder,
)

logger = logging.getLogger("slack_routes")

router = APIRouter(prefix="/slack", tags=["Slack Integration"])


def verify_slack_signature(
    timestamp: str,
    signature: str,
    body: bytes
) -> bool:
    """
    Verify the incoming Slack request signature.

    Slack signs all requests using HMAC-SHA256. We verify this signature
    to ensure the request actually came from Slack.
    """
    if not SLACK_SIGNING_SECRET:
        logger.warning("Slack signing secret not configured")
        return False

    # Check timestamp to prevent replay attacks (5 minute window)
    try:
        request_time = int(timestamp)
        if abs(time.time() - request_time) > 300:
            logger.warning("Slack request timestamp too old")
            return False
    except ValueError:
        return False

    # Calculate expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_signature = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_signature, signature)


async def get_verified_slack_body(request: Request) -> bytes:
    """
    Get the request body after verifying Slack signature.

    Raises HTTPException if verification fails.
    """
    body = await request.body()

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not verify_slack_signature(timestamp, signature, body):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return body


# =============================================================================
# SLACK EVENTS ENDPOINT
# =============================================================================

@router.post("/events")
async def handle_slack_events(request: Request):
    """
    Handle incoming Slack events.

    This endpoint receives:
    - URL verification challenges (for app setup)
    - App home opened events
    - App uninstalled events
    - Message events (if subscribed)

    Slack expects a response within 3 seconds, so heavy processing
    should be done asynchronously.
    """
    if not is_slack_app_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    body = await get_verified_slack_body(request)
    payload = json.loads(body)

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return JSONResponse({"challenge": payload.get("challenge")})

    # Use slack-bolt handler for other events
    handler = create_slack_handler()
    if handler:
        return await handler.handle(request)

    # Fallback: acknowledge the event
    return JSONResponse({"ok": True})


# =============================================================================
# SLASH COMMANDS ENDPOINT
# =============================================================================

@router.post("/commands")
async def handle_slack_commands(request: Request):
    """
    Handle incoming Slack slash commands.

    Commands:
    - /readin summary - Get latest meeting summary
    - /readin actions - Get pending action items
    - /readin meetings - Show recent meetings
    - /readin help - Show help

    Slack sends slash commands as form-urlencoded data.
    We need to respond within 3 seconds with an immediate acknowledgment,
    then send the actual response via the response_url if needed.
    """
    if not is_slack_app_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    body = await get_verified_slack_body(request)

    # Use slack-bolt handler
    handler = create_slack_handler()
    if handler:
        return await handler.handle(request)

    # Fallback response
    return JSONResponse({
        "response_type": "ephemeral",
        "text": "ReadIn AI is not fully configured. Please contact support."
    })


# =============================================================================
# INTERACTIONS ENDPOINT
# =============================================================================

@router.post("/interactions")
async def handle_slack_interactions(request: Request):
    """
    Handle interactive component callbacks.

    This endpoint receives:
    - Button clicks (e.g., "Complete Action", "View Details")
    - Modal submissions
    - Shortcut triggers

    The payload is JSON wrapped in a form field called 'payload'.
    """
    if not is_slack_app_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    body = await get_verified_slack_body(request)

    # Use slack-bolt handler
    handler = create_slack_handler()
    if handler:
        return await handler.handle(request)

    # Fallback acknowledgment
    return Response(status_code=200)


# =============================================================================
# OAUTH ROUTES (complement to existing integrations.py)
# =============================================================================

@router.get("/install")
async def slack_install():
    """
    Get the Slack app installation URL.

    Users click this to add ReadIn AI to their Slack workspace.
    """
    if not is_slack_app_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    from config import SLACK_CLIENT_ID, APP_URL

    scopes = [
        "chat:write",
        "channels:read",
        "groups:read",
        "im:write",
        "users:read",
        "commands",
    ]

    install_url = (
        f"https://slack.com/oauth/v2/authorize?"
        f"client_id={SLACK_CLIENT_ID}&"
        f"scope={','.join(scopes)}&"
        f"redirect_uri={APP_URL}/api/v1/integrations/slack/callback"
    )

    return {"install_url": install_url}


# =============================================================================
# NOTIFICATION TRIGGERS (Internal API)
# =============================================================================

@router.post("/notify/meeting-summary")
async def trigger_meeting_summary_notification(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger a meeting summary notification to Slack.

    Internal endpoint called by the summary generation worker.

    Body:
    {
        "user_id": int,
        "meeting_id": int,
        "summary_text": str,
        "key_points": list[str],
        "action_count": int
    }
    """
    # This should be protected - verify it's an internal call
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        raise HTTPException(status_code=403, detail="Internal access only")

    try:
        body = await request.json()

        await send_meeting_summary_notification(
            user_id=body["user_id"],
            meeting_id=body["meeting_id"],
            summary_text=body.get("summary_text", ""),
            key_points=body.get("key_points", []),
            action_count=body.get("action_count", 0)
        )

        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Failed to send meeting notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/action-reminder")
async def trigger_action_reminder(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger an action item reminder to Slack.

    Internal endpoint called by the reminder scheduler.

    Body:
    {
        "user_id": int,
        "action_item_id": int
    }
    """
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        raise HTTPException(status_code=403, detail="Internal access only")

    try:
        body = await request.json()

        await send_action_item_reminder(
            user_id=body["user_id"],
            action_item_id=body["action_item_id"]
        )

        return {"status": "sent"}
    except Exception as e:
        logger.error(f"Failed to send action reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digest/trigger")
async def trigger_daily_digest(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Trigger daily digest for all users or a specific user.

    Internal endpoint called by the scheduler.

    Body:
    {
        "user_id": int (optional - if not provided, sends to all)
    }
    """
    internal_key = request.headers.get("X-Internal-Key")
    if not internal_key:
        raise HTTPException(status_code=403, detail="Internal access only")

    try:
        body = await request.json() if await request.body() else {}

        digest = SlackDailyDigest()

        if "user_id" in body:
            await digest.send_daily_digest(body["user_id"])
            return {"status": "sent", "user_id": body["user_id"]}
        else:
            await digest.send_all_daily_digests()
            return {"status": "sent_all"}

    except Exception as e:
        logger.error(f"Failed to send digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def slack_health():
    """
    Check Slack integration health.

    Returns configuration status and connectivity.
    """
    from config import SLACK_CLIENT_ID, SLACK_CLIENT_SECRET

    return {
        "configured": is_slack_app_configured(),
        "client_id_set": bool(SLACK_CLIENT_ID),
        "client_secret_set": bool(SLACK_CLIENT_SECRET),
        "signing_secret_set": bool(SLACK_SIGNING_SECRET),
    }
