"""
Integration routes for Slack, Microsoft Teams, Video Platforms, and Calendar Services.

PRIVACY-FIRST VIDEO INTEGRATIONS (STEALTH MODE):
- NO bots join meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth authorization flows
- Token management
- Integration settings
- Notification delivery
- Meeting schedule sync (Zoom, Google Meet, Teams, Webex, Apple Calendar, Calendly)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserIntegration, IntegrationProvider
from auth import get_current_user
from services.slack_service import SlackService, is_slack_configured
from services.teams_service import TeamsService, is_teams_configured
from services.zoom_service import ZoomService, is_zoom_configured
from services.google_meet_service import GoogleMeetService, is_google_meet_configured
from services.teams_meeting_service import TeamsMeetingService, is_teams_meeting_configured
from services.webex_service import WebexService, is_webex_configured
from services.apple_calendar_service import AppleCalendarService, is_apple_calendar_configured
from services.calendly_service import CalendlyService, is_calendly_configured
from config import APP_URL

logger = logging.getLogger("integrations")
router = APIRouter(prefix="/integrations", tags=["integrations"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class IntegrationStatus(BaseModel):
    """Integration connection status."""
    provider: str
    is_connected: bool
    workspace_name: Optional[str] = None
    user_name: Optional[str] = None
    default_channel: Optional[str] = None
    connected_at: Optional[datetime] = None
    notifications_enabled: bool = True
    meeting_summaries_enabled: bool = True
    action_item_reminders_enabled: bool = True


class IntegrationSettings(BaseModel):
    """Settings for an integration."""
    notifications_enabled: bool = True
    meeting_summaries_enabled: bool = True
    action_item_reminders_enabled: bool = True
    briefing_notifications_enabled: bool = True
    default_channel_id: Optional[str] = None


class ChannelInfo(BaseModel):
    """Channel/team information."""
    id: str
    name: str
    is_private: bool = False


class TestMessageRequest(BaseModel):
    """Request to send a test message."""
    channel_id: str


# =============================================================================
# LIST INTEGRATIONS
# =============================================================================

@router.get("/status")
async def get_integrations_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all available integrations for the current user.
    """
    integrations = []

    # Get user's connected integrations
    user_integrations = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.is_active == True
    ).all()

    integration_map = {i.provider: i for i in user_integrations}

    # Slack status
    slack_integration = integration_map.get(IntegrationProvider.SLACK)
    integrations.append({
        "provider": "slack",
        "display_name": "Slack",
        "is_configured": is_slack_configured(),
        "is_connected": slack_integration is not None,
        "workspace_name": slack_integration.provider_team_name if slack_integration else None,
        "user_name": slack_integration.display_name if slack_integration else None,
        "default_channel": slack_integration.default_channel_name if slack_integration else None,
        "connected_at": slack_integration.connected_at if slack_integration else None,
        "notifications_enabled": slack_integration.notifications_enabled if slack_integration else True,
        "meeting_summaries_enabled": slack_integration.meeting_summaries_enabled if slack_integration else True,
        "action_item_reminders_enabled": slack_integration.action_item_reminders_enabled if slack_integration else True,
    })

    # Teams status
    teams_integration = integration_map.get(IntegrationProvider.TEAMS)
    integrations.append({
        "provider": "teams",
        "display_name": "Microsoft Teams",
        "is_configured": is_teams_configured(),
        "is_connected": teams_integration is not None,
        "workspace_name": teams_integration.provider_team_name if teams_integration else None,
        "user_name": teams_integration.display_name if teams_integration else None,
        "default_channel": teams_integration.default_channel_name if teams_integration else None,
        "connected_at": teams_integration.connected_at if teams_integration else None,
        "notifications_enabled": teams_integration.notifications_enabled if teams_integration else True,
        "meeting_summaries_enabled": teams_integration.meeting_summaries_enabled if teams_integration else True,
        "action_item_reminders_enabled": teams_integration.action_item_reminders_enabled if teams_integration else True,
    })

    return {"integrations": integrations}


# =============================================================================
# SLACK OAUTH
# =============================================================================

@router.get("/slack/authorize")
async def slack_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Slack OAuth authorization URL.
    """
    if not is_slack_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    slack_service = SlackService(db)
    redirect_uri = f"{APP_URL}/api/integrations/slack/callback"
    auth_url = slack_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/slack/callback")
async def slack_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle Slack OAuth callback.
    """
    if not is_slack_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    # Parse state to get user_id
    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for token
    slack_service = SlackService(db)
    redirect_uri = f"{APP_URL}/api/integrations/slack/callback"
    result = await slack_service.exchange_code(code, redirect_uri)
    await slack_service.close()

    if not result.get("success"):
        logger.error(f"Slack OAuth failed: {result.get('error')}")
        # Redirect to dashboard with error
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings?error=slack_auth_failed"}
        )

    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.SLACK
    ).first()

    if existing:
        # Update existing integration
        existing.access_token = result.get("access_token")
        existing.provider_team_id = result.get("team_id")
        existing.provider_team_name = result.get("team_name")
        existing.provider_user_id = result.get("bot_user_id")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        # Create new integration
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.SLACK,
            access_token=result.get("access_token"),
            provider_team_id=result.get("team_id"),
            provider_team_name=result.get("team_name"),
            provider_user_id=result.get("bot_user_id"),
        )
        db.add(integration)

    db.commit()

    # Redirect to dashboard with success
    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings?success=slack_connected"}
    )


@router.get("/slack/channels")
async def get_slack_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of Slack channels the bot can post to.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SLACK,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Slack not connected")

    slack_service = SlackService(db)
    channels = await slack_service.list_channels(integration.access_token)
    await slack_service.close()

    return {"channels": channels}


@router.delete("/slack")
async def disconnect_slack(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect Slack integration.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SLACK
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Slack disconnected"}


# =============================================================================
# TEAMS OAUTH
# =============================================================================

@router.get("/teams/authorize")
async def teams_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Microsoft Teams OAuth authorization URL.
    """
    if not is_teams_configured():
        raise HTTPException(status_code=503, detail="Teams integration not configured")

    teams_service = TeamsService(db)
    redirect_uri = f"{APP_URL}/api/integrations/teams/callback"
    auth_url = teams_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/teams/callback")
async def teams_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle Microsoft Teams OAuth callback.
    """
    if not is_teams_configured():
        raise HTTPException(status_code=503, detail="Teams integration not configured")

    # Parse state to get user_id
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for token
    teams_service = TeamsService(db)
    redirect_uri = f"{APP_URL}/api/integrations/teams/callback"
    result = await teams_service.exchange_code(code, redirect_uri)
    await teams_service.close()

    if not result.get("success"):
        logger.error(f"Teams OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings?error=teams_auth_failed"}
        )

    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.TEAMS
    ).first()

    if existing:
        # Update existing integration
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        # Create new integration
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.TEAMS,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings?success=teams_connected"}
    )


@router.get("/teams/teams")
async def get_teams_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of Teams the user belongs to.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.TEAMS,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Teams not connected")

    teams_service = TeamsService(db)

    # Refresh token if expired
    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await teams_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await teams_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    teams = await teams_service.list_teams(integration.access_token)
    await teams_service.close()

    return {"teams": teams}


@router.get("/teams/channels/{team_id}")
async def get_teams_channels(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of channels in a specific Team.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.TEAMS,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Teams not connected")

    teams_service = TeamsService(db)
    channels = await teams_service.list_channels(integration.access_token, team_id)
    await teams_service.close()

    return {"channels": channels}


@router.delete("/teams")
async def disconnect_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect Microsoft Teams integration.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.TEAMS
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Teams disconnected"}


# =============================================================================
# INTEGRATION SETTINGS
# =============================================================================

@router.put("/{provider}/settings")
async def update_integration_settings(
    provider: str,
    settings: IntegrationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update settings for an integration.
    """
    if provider not in [IntegrationProvider.SLACK, IntegrationProvider.TEAMS]:
        raise HTTPException(status_code=400, detail="Invalid provider")

    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == provider,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    # Update settings
    integration.notifications_enabled = settings.notifications_enabled
    integration.meeting_summaries_enabled = settings.meeting_summaries_enabled
    integration.action_item_reminders_enabled = settings.action_item_reminders_enabled
    integration.briefing_notifications_enabled = settings.briefing_notifications_enabled

    if settings.default_channel_id:
        integration.default_channel_id = settings.default_channel_id

    integration.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Settings updated"}


# =============================================================================
# TEST NOTIFICATIONS
# =============================================================================

@router.post("/{provider}/test")
async def send_test_notification(
    provider: str,
    request: TestMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a test notification to verify integration is working.
    """
    if provider not in [IntegrationProvider.SLACK, IntegrationProvider.TEAMS]:
        raise HTTPException(status_code=400, detail="Invalid provider")

    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == provider,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    if provider == IntegrationProvider.SLACK:
        slack_service = SlackService(db)
        result = await slack_service.send_message(
            access_token=integration.access_token,
            channel=request.channel_id,
            text="ReadIn AI test notification - Your integration is working correctly!",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*ReadIn AI Test Notification*\n\nYour Slack integration is working correctly! You'll receive meeting summaries and action item reminders in this channel."
                    }
                }
            ]
        )
        await slack_service.close()

    else:  # Teams
        teams_service = TeamsService(db)

        # For Teams, we need team_id and channel_id
        # The channel_id format is typically: team_id:channel_id
        parts = request.channel_id.split(":")
        if len(parts) != 2:
            await teams_service.close()
            raise HTTPException(status_code=400, detail="Invalid channel ID format. Use team_id:channel_id")

        team_id, channel_id = parts
        result = await teams_service.send_channel_message(
            access_token=integration.access_token,
            team_id=team_id,
            channel_id=channel_id,
            content="<b>ReadIn AI Test Notification</b><br><br>Your Teams integration is working correctly! You'll receive meeting summaries and action item reminders in this channel."
        )
        await teams_service.close()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"Failed to send test message: {result.get('error')}")

    # Update default channel
    integration.default_channel_id = request.channel_id
    integration.last_used_at = datetime.utcnow()
    db.commit()

    return {"message": "Test notification sent successfully"}


# =============================================================================
# SLACK WEBHOOK (FOR SLASH COMMANDS)
# =============================================================================

@router.post("/slack/webhook")
async def slack_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle incoming Slack webhooks (slash commands, interactivity).
    """
    if not is_slack_configured():
        raise HTTPException(status_code=503, detail="Slack integration not configured")

    # Get headers for verification
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    body = await request.body()

    # Verify request
    slack_service = SlackService(db)
    if not slack_service.verify_request(timestamp, signature, body):
        await slack_service.close()
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse form data
    form_data = await request.form()
    command = form_data.get("command", "")
    text = form_data.get("text", "")
    user_id = form_data.get("user_id", "")
    channel_id = form_data.get("channel_id", "")
    response_url = form_data.get("response_url", "")

    # Handle command
    result = await slack_service.handle_slash_command(
        command=command,
        text=text,
        user_id=user_id,
        channel_id=channel_id,
        response_url=response_url
    )
    await slack_service.close()

    return result


# =============================================================================
# VIDEO PLATFORM INTEGRATIONS (STEALTH MODE)
# =============================================================================
# These integrations ONLY sync calendar data for meeting detection.
# NO bots join meetings - audio capture is done locally by the desktop app.
# Other meeting participants CANNOT see that ReadIn AI is being used.
# =============================================================================


# =============================================================================
# ZOOM OAUTH (Calendar sync only - NO bot joining)
# =============================================================================

@router.get("/zoom/authorize")
async def zoom_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Zoom OAuth authorization URL for calendar sync.

    PRIVACY NOTE: This only grants calendar read access.
    No bot will join meetings - audio is captured locally.
    """
    if not is_zoom_configured():
        raise HTTPException(status_code=503, detail="Zoom integration not configured")

    zoom_service = ZoomService(db)
    redirect_uri = f"{APP_URL}/api/integrations/zoom/callback"
    auth_url = zoom_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/zoom/callback")
async def zoom_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle Zoom OAuth callback.
    """
    if not is_zoom_configured():
        raise HTTPException(status_code=503, detail="Zoom integration not configured")

    # Parse state to get user_id
    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for token
    zoom_service = ZoomService(db)
    redirect_uri = f"{APP_URL}/api/integrations/zoom/callback"
    result = await zoom_service.exchange_code(code, redirect_uri)
    await zoom_service.close()

    if not result.get("success"):
        logger.error(f"Zoom OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=zoom_auth_failed"}
        )

    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.ZOOM
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.ZOOM,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=zoom_connected"}
    )


@router.get("/zoom/meetings")
async def get_zoom_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get upcoming Zoom meetings for meeting detection.
    Used by desktop app to know when to activate.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.ZOOM,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Zoom not connected")

    zoom_service = ZoomService(db)

    # Refresh token if expired
    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await zoom_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await zoom_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    meetings = await zoom_service.get_upcoming_meetings(integration.access_token)
    await zoom_service.close()

    return {"meetings": meetings, "platform": "zoom"}


@router.delete("/zoom")
async def disconnect_zoom(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Zoom integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.ZOOM
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Zoom disconnected"}


# =============================================================================
# GOOGLE MEET OAUTH (Calendar sync only - NO bot joining)
# =============================================================================

@router.get("/google-meet/authorize")
async def google_meet_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Google OAuth authorization URL for calendar sync.

    PRIVACY NOTE: Only requests calendar read access.
    No bot joins meetings - audio capture is local.
    """
    if not is_google_meet_configured():
        raise HTTPException(status_code=503, detail="Google Meet integration not configured")

    google_service = GoogleMeetService(db)
    redirect_uri = f"{APP_URL}/api/integrations/google-meet/callback"
    auth_url = google_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/google-meet/callback")
async def google_meet_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback."""
    if not is_google_meet_configured():
        raise HTTPException(status_code=503, detail="Google Meet integration not configured")

    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    google_service = GoogleMeetService(db)
    redirect_uri = f"{APP_URL}/api/integrations/google-meet/callback"
    result = await google_service.exchange_code(code, redirect_uri)
    await google_service.close()

    if not result.get("success"):
        logger.error(f"Google OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=google_auth_failed"}
        )

    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.GOOGLE_MEET
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.GOOGLE_MEET,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=google_connected"}
    )


@router.get("/google-meet/meetings")
async def get_google_meet_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming Google Meet meetings from calendar."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.GOOGLE_MEET,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Google Meet not connected")

    google_service = GoogleMeetService(db)

    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await google_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            if refresh_result.get("refresh_token"):
                integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await google_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    meetings = await google_service.get_upcoming_meetings(integration.access_token)
    await google_service.close()

    return {"meetings": meetings, "platform": "google_meet"}


@router.delete("/google-meet")
async def disconnect_google_meet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Google Meet integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.GOOGLE_MEET
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Google Meet disconnected"}


# =============================================================================
# MICROSOFT TEAMS MEETINGS OAUTH (Calendar sync only - NO bot joining)
# =============================================================================

@router.get("/teams-meeting/authorize")
async def teams_meeting_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Microsoft OAuth URL for Teams meeting calendar sync.

    PRIVACY NOTE: Only requests calendar read access.
    No bot joins meetings - completely invisible.
    """
    if not is_teams_meeting_configured():
        raise HTTPException(status_code=503, detail="Teams Meeting integration not configured")

    teams_service = TeamsMeetingService(db)
    redirect_uri = f"{APP_URL}/api/integrations/teams-meeting/callback"
    auth_url = teams_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/teams-meeting/callback")
async def teams_meeting_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Microsoft Teams Meeting OAuth callback."""
    if not is_teams_meeting_configured():
        raise HTTPException(status_code=503, detail="Teams Meeting integration not configured")

    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    teams_service = TeamsMeetingService(db)
    redirect_uri = f"{APP_URL}/api/integrations/teams-meeting/callback"
    result = await teams_service.exchange_code(code, redirect_uri)
    await teams_service.close()

    if not result.get("success"):
        logger.error(f"Teams Meeting OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=teams_meeting_auth_failed"}
        )

    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.MICROSOFT_TEAMS_MEETING
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.MICROSOFT_TEAMS_MEETING,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=teams_meeting_connected"}
    )


@router.get("/teams-meeting/meetings")
async def get_teams_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming Teams meetings from calendar."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.MICROSOFT_TEAMS_MEETING,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Teams Meeting not connected")

    teams_service = TeamsMeetingService(db)

    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await teams_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await teams_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    meetings = await teams_service.get_upcoming_meetings(integration.access_token)
    await teams_service.close()

    return {"meetings": meetings, "platform": "microsoft_teams"}


@router.delete("/teams-meeting")
async def disconnect_teams_meeting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Teams Meeting integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.MICROSOFT_TEAMS_MEETING
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Teams Meeting disconnected"}


# =============================================================================
# CISCO WEBEX OAUTH (Calendar sync only - NO bot joining)
# =============================================================================

@router.get("/webex/authorize")
async def webex_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Webex OAuth authorization URL for meeting sync.

    PRIVACY NOTE: Only requests meeting schedule access.
    No bot joins meetings - completely invisible.
    """
    if not is_webex_configured():
        raise HTTPException(status_code=503, detail="Webex integration not configured")

    webex_service = WebexService(db)
    redirect_uri = f"{APP_URL}/api/integrations/webex/callback"
    auth_url = webex_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/webex/callback")
async def webex_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Webex OAuth callback."""
    if not is_webex_configured():
        raise HTTPException(status_code=503, detail="Webex integration not configured")

    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    webex_service = WebexService(db)
    redirect_uri = f"{APP_URL}/api/integrations/webex/callback"
    result = await webex_service.exchange_code(code, redirect_uri)
    await webex_service.close()

    if not result.get("success"):
        logger.error(f"Webex OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=webex_auth_failed"}
        )

    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.WEBEX
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.WEBEX,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=webex_connected"}
    )


@router.get("/webex/meetings")
async def get_webex_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming Webex meetings."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.WEBEX,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Webex not connected")

    webex_service = WebexService(db)

    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await webex_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await webex_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    meetings = await webex_service.get_upcoming_meetings(integration.access_token)
    await webex_service.close()

    return {"meetings": meetings, "platform": "webex"}


@router.delete("/webex")
async def disconnect_webex(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Webex integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.WEBEX
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Webex disconnected"}


# =============================================================================
# APPLE CALENDAR OAUTH (CalDAV-based calendar sync)
# =============================================================================

@router.get("/apple-calendar/authorize")
async def apple_calendar_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Apple OAuth authorization URL for calendar sync.

    PRIVACY NOTE: Only requests calendar access via CalDAV.
    No bot joins meetings - completely invisible.
    """
    if not is_apple_calendar_configured():
        raise HTTPException(status_code=503, detail="Apple Calendar integration not configured")

    apple_service = AppleCalendarService(db)
    redirect_uri = f"{APP_URL}/api/integrations/apple-calendar/callback"
    auth_url = apple_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/apple-calendar/callback")
async def apple_calendar_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Apple Calendar OAuth callback."""
    if not is_apple_calendar_configured():
        raise HTTPException(status_code=503, detail="Apple Calendar integration not configured")

    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    apple_service = AppleCalendarService(db)
    redirect_uri = f"{APP_URL}/api/integrations/apple-calendar/callback"
    result = await apple_service.exchange_code(code, redirect_uri)
    await apple_service.close()

    if not result.get("success"):
        logger.error(f"Apple Calendar OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=apple_auth_failed"}
        )

    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.APPLE_CALENDAR
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.APPLE_CALENDAR,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=apple_calendar_connected"}
    )


@router.get("/apple-calendar/events")
async def get_apple_calendar_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming events from Apple Calendar via CalDAV."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.APPLE_CALENDAR,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Apple Calendar not connected")

    apple_service = AppleCalendarService(db)

    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await apple_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            if refresh_result.get("refresh_token"):
                integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 3600))
            db.commit()
        else:
            await apple_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    events = await apple_service.get_upcoming_meetings(
        integration.access_token,
        integration.provider_user_id
    )
    await apple_service.close()

    return {"events": events, "platform": "apple_calendar"}


@router.get("/apple-calendar/calendars")
async def get_apple_calendars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of user's Apple Calendar calendars."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.APPLE_CALENDAR,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Apple Calendar not connected")

    apple_service = AppleCalendarService(db)
    calendars = await apple_service.get_calendars(
        integration.access_token,
        integration.provider_user_id
    )
    await apple_service.close()

    return {"calendars": calendars}


class CreateEventRequest(BaseModel):
    """Request to create a calendar event."""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    calendar_id: str = "calendar"


@router.post("/apple-calendar/events")
async def create_apple_calendar_event(
    request: CreateEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new event in Apple Calendar."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.APPLE_CALENDAR,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Apple Calendar not connected")

    apple_service = AppleCalendarService(db)
    event = await apple_service.create_event(
        access_token=integration.access_token,
        user_id=integration.provider_user_id,
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        description=request.description,
        location=request.location,
        attendees=request.attendees,
        calendar_id=request.calendar_id,
    )
    await apple_service.close()

    if not event:
        raise HTTPException(status_code=500, detail="Failed to create event")

    return {"event": event, "message": "Event created successfully"}


@router.delete("/apple-calendar")
async def disconnect_apple_calendar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Apple Calendar integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.APPLE_CALENDAR
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Apple Calendar disconnected"}


# =============================================================================
# CALENDLY OAUTH (Scheduling integration with webhooks)
# =============================================================================

@router.get("/calendly/authorize")
async def calendly_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Calendly OAuth authorization URL.

    Integrates with Calendly for scheduled meeting detection
    and webhook notifications for new bookings.
    """
    if not is_calendly_configured():
        raise HTTPException(status_code=503, detail="Calendly integration not configured")

    calendly_service = CalendlyService(db)
    redirect_uri = f"{APP_URL}/api/integrations/calendly/callback"
    auth_url = calendly_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/calendly/callback")
async def calendly_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Calendly OAuth callback."""
    if not is_calendly_configured():
        raise HTTPException(status_code=503, detail="Calendly integration not configured")

    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    calendly_service = CalendlyService(db)
    redirect_uri = f"{APP_URL}/api/integrations/calendly/callback"
    result = await calendly_service.exchange_code(code, redirect_uri)
    await calendly_service.close()

    if not result.get("success"):
        logger.error(f"Calendly OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=calendly_auth_failed"}
        )

    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.CALENDLY
    ).first()

    # Store extra metadata in a JSON field or separate columns
    extra_data = {
        "user_uri": result.get("user_uri"),
        "organization_uri": result.get("organization_uri"),
    }

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 7200))
        existing.provider_user_id = result.get("user_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.CALENDLY,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 7200)),
            provider_user_id=result.get("user_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=calendly_connected"}
    )


@router.get("/calendly/events")
async def get_calendly_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upcoming Calendly scheduled events."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.CALENDLY,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Calendly not connected")

    calendly_service = CalendlyService(db)

    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await calendly_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 7200))
            db.commit()
        else:
            await calendly_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    events = await calendly_service.get_upcoming_meetings(integration.access_token)
    await calendly_service.close()

    return {"events": events, "platform": "calendly"}


@router.get("/calendly/events/{event_id}")
async def get_calendly_event_details(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details for a specific Calendly event."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.CALENDLY,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Calendly not connected")

    calendly_service = CalendlyService(db)
    event = await calendly_service.get_event_details(integration.access_token, event_id)
    await calendly_service.close()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"event": event}


@router.get("/calendly/events/{event_id}/invitees")
async def get_calendly_event_invitees(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get invitees for a Calendly event."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.CALENDLY,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Calendly not connected")

    calendly_service = CalendlyService(db)
    invitees = await calendly_service.get_event_invitees(integration.access_token, event_id)
    await calendly_service.close()

    return {"invitees": invitees}


@router.get("/calendly/event-types")
async def get_calendly_event_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's Calendly event types."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.CALENDLY,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Calendly not connected")

    calendly_service = CalendlyService(db)
    event_types = await calendly_service.get_event_types(integration.access_token)
    await calendly_service.close()

    return {"event_types": event_types}


@router.post("/calendly/webhook")
async def calendly_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle incoming Calendly webhook events.

    Processes booking notifications for:
    - invitee.created (new booking)
    - invitee.canceled (booking canceled)
    - invitee_no_show.created (no-show marked)
    """
    if not is_calendly_configured():
        raise HTTPException(status_code=503, detail="Calendly integration not configured")

    # Get headers for verification
    signature = request.headers.get("Calendly-Webhook-Signature", "")
    body = await request.body()

    # Verify webhook signature
    calendly_service = CalendlyService(db)

    # Parse the timestamp from signature header (format: t=timestamp,v1=signature)
    timestamp = ""
    sig_value = ""
    for part in signature.split(","):
        if part.startswith("t="):
            timestamp = part[2:]
        elif part.startswith("v1="):
            sig_value = part[3:]

    if not calendly_service.verify_webhook_signature(sig_value, timestamp, body):
        await calendly_service.close()
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse webhook payload
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        await calendly_service.close()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event")
    result = await calendly_service.handle_webhook_event(event_type, payload)
    await calendly_service.close()

    # Log the webhook for debugging
    logger.info(f"Calendly webhook received: {event_type}")

    return {"status": "received", "event_type": event_type, "processed": result}


@router.delete("/calendly")
async def disconnect_calendly(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Calendly integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.CALENDLY
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Calendly disconnected"}


# =============================================================================
# UNIFIED MEETING DETECTION (For Desktop App)
# =============================================================================

@router.get("/meetings/upcoming")
async def get_all_upcoming_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all upcoming meetings across all connected video platforms.

    PRIVACY NOTE: This only returns meeting schedule data.
    No bots will join meetings - all audio capture is local.

    Used by desktop app to show upcoming meetings and detect when to activate.
    """
    from services.meeting_detector import MeetingDetector

    detector = MeetingDetector(db)
    meetings = await detector.get_all_upcoming_meetings(current_user.id)

    return {
        "meetings": meetings,
        "stealth_mode": True,
        "privacy_note": "Audio capture is done locally. No bot joins meetings."
    }


@router.get("/meetings/active")
async def check_active_meeting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if user is currently in any meeting.

    Used by desktop app to detect meeting state for auto-activation.
    """
    from services.meeting_detector import MeetingDetector

    detector = MeetingDetector(db)
    active = await detector.check_active_meeting(current_user.id)

    return {
        "active_meeting": active,
        "is_in_meeting": active is not None,
        "stealth_mode": True
    }


# =============================================================================
# VIDEO PLATFORM STATUS
# =============================================================================

@router.get("/video-platforms/status")
async def get_video_platforms_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all video platform integrations.

    STEALTH MODE: These integrations sync calendars only.
    No bots join meetings - completely invisible to other participants.
    """
    integrations = []

    user_integrations = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.is_active == True
    ).all()

    integration_map = {i.provider: i for i in user_integrations}

    # Zoom
    zoom_int = integration_map.get(IntegrationProvider.ZOOM)
    integrations.append({
        "provider": "zoom",
        "display_name": "Zoom",
        "is_configured": is_zoom_configured(),
        "is_connected": zoom_int is not None,
        "email": zoom_int.email if zoom_int else None,
        "display_name_user": zoom_int.display_name if zoom_int else None,
        "connected_at": zoom_int.connected_at if zoom_int else None,
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    # Google Meet
    google_int = integration_map.get(IntegrationProvider.GOOGLE_MEET)
    integrations.append({
        "provider": "google_meet",
        "display_name": "Google Meet",
        "is_configured": is_google_meet_configured(),
        "is_connected": google_int is not None,
        "email": google_int.email if google_int else None,
        "display_name_user": google_int.display_name if google_int else None,
        "connected_at": google_int.connected_at if google_int else None,
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    # Microsoft Teams Meeting
    teams_int = integration_map.get(IntegrationProvider.MICROSOFT_TEAMS_MEETING)
    integrations.append({
        "provider": "microsoft_teams",
        "display_name": "Microsoft Teams",
        "is_configured": is_teams_meeting_configured(),
        "is_connected": teams_int is not None,
        "email": teams_int.email if teams_int else None,
        "display_name_user": teams_int.display_name if teams_int else None,
        "connected_at": teams_int.connected_at if teams_int else None,
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    # Webex
    webex_int = integration_map.get(IntegrationProvider.WEBEX)
    integrations.append({
        "provider": "webex",
        "display_name": "Cisco Webex",
        "is_configured": is_webex_configured(),
        "is_connected": webex_int is not None,
        "email": webex_int.email if webex_int else None,
        "display_name_user": webex_int.display_name if webex_int else None,
        "connected_at": webex_int.connected_at if webex_int else None,
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    return {
        "video_platforms": integrations,
        "stealth_mode_explanation": (
            "ReadIn AI operates in STEALTH MODE. "
            "Other meeting participants CANNOT see that you are using AI assistance. "
            "No bots or AI agents join your meetings. "
            "Audio is captured locally by the desktop app and processed securely. "
            "Calendar sync is used only to detect meeting schedules."
        )
    }


# =============================================================================
# CALENDAR INTEGRATIONS STATUS
# =============================================================================

@router.get("/calendar-platforms/status")
async def get_calendar_platforms_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all calendar platform integrations.

    Includes both video platform calendars and standalone calendar services.
    """
    integrations = []

    user_integrations = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.is_active == True
    ).all()

    integration_map = {i.provider: i for i in user_integrations}

    # Apple Calendar
    apple_int = integration_map.get(IntegrationProvider.APPLE_CALENDAR)
    integrations.append({
        "provider": "apple_calendar",
        "display_name": "Apple Calendar",
        "is_configured": is_apple_calendar_configured(),
        "is_connected": apple_int is not None,
        "email": apple_int.email if apple_int else None,
        "display_name_user": apple_int.display_name if apple_int else None,
        "connected_at": apple_int.connected_at if apple_int else None,
        "features": ["event_sync", "event_creation", "caldav"],
        "stealth_mode": True,
        "privacy_note": "CalDAV sync only - no bot joins meetings"
    })

    # Calendly
    calendly_int = integration_map.get(IntegrationProvider.CALENDLY)
    integrations.append({
        "provider": "calendly",
        "display_name": "Calendly",
        "is_configured": is_calendly_configured(),
        "is_connected": calendly_int is not None,
        "email": calendly_int.email if calendly_int else None,
        "display_name_user": calendly_int.display_name if calendly_int else None,
        "connected_at": calendly_int.connected_at if calendly_int else None,
        "features": ["event_sync", "webhook_notifications", "invitee_info"],
        "stealth_mode": True,
        "privacy_note": "Schedule sync only - no bot joins meetings"
    })

    # Google Calendar (via Google Meet integration)
    google_int = integration_map.get(IntegrationProvider.GOOGLE_MEET)
    integrations.append({
        "provider": "google_calendar",
        "display_name": "Google Calendar",
        "is_configured": is_google_meet_configured(),
        "is_connected": google_int is not None,
        "email": google_int.email if google_int else None,
        "display_name_user": google_int.display_name if google_int else None,
        "connected_at": google_int.connected_at if google_int else None,
        "features": ["event_sync", "meet_detection"],
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    # Microsoft Outlook Calendar (via Teams Meeting integration)
    teams_int = integration_map.get(IntegrationProvider.MICROSOFT_TEAMS_MEETING)
    integrations.append({
        "provider": "outlook_calendar",
        "display_name": "Microsoft Outlook",
        "is_configured": is_teams_meeting_configured(),
        "is_connected": teams_int is not None,
        "email": teams_int.email if teams_int else None,
        "display_name_user": teams_int.display_name if teams_int else None,
        "connected_at": teams_int.connected_at if teams_int else None,
        "features": ["event_sync", "teams_detection"],
        "stealth_mode": True,
        "privacy_note": "Calendar sync only - no bot joins meetings"
    })

    return {
        "calendar_platforms": integrations,
        "total_connected": len([i for i in integrations if i["is_connected"]]),
        "stealth_mode_explanation": (
            "ReadIn AI syncs your calendar data to detect meeting schedules. "
            "No bots or AI agents join your meetings. "
            "Audio is captured locally by the desktop app."
        )
    }


# =============================================================================
# SALESFORCE CRM INTEGRATION
# =============================================================================

from services.salesforce_service import SalesforceService, is_salesforce_configured


class SalesforceSyncSettings(BaseModel):
    """Settings for Salesforce sync."""
    auto_sync_contacts: bool = True
    auto_log_meetings: bool = True
    auto_sync_notes: bool = False
    auto_create_tasks: bool = False


class SalesforceMeetingSyncRequest(BaseModel):
    """Request to sync a meeting to Salesforce."""
    meeting_id: int
    participants: Optional[List[dict]] = None
    include_notes: bool = False
    include_action_items: bool = True


@router.get("/salesforce/authorize")
async def salesforce_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get Salesforce OAuth authorization URL.
    """
    if not is_salesforce_configured():
        raise HTTPException(status_code=503, detail="Salesforce integration not configured")

    salesforce_service = SalesforceService(db)
    redirect_uri = f"{APP_URL}/api/integrations/salesforce/callback"
    auth_url = salesforce_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/salesforce/callback")
async def salesforce_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle Salesforce OAuth callback.
    """
    if not is_salesforce_configured():
        raise HTTPException(status_code=503, detail="Salesforce integration not configured")

    # Parse state to get user_id
    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for token
    salesforce_service = SalesforceService(db)
    redirect_uri = f"{APP_URL}/api/integrations/salesforce/callback"
    result = await salesforce_service.exchange_code(code, redirect_uri)
    await salesforce_service.close()

    if not result.get("success"):
        logger.error(f"Salesforce OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=salesforce_auth_failed"}
        )

    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.instance_url = result.get("instance_url")
        existing.provider_user_id = result.get("user_id")
        existing.org_id = result.get("org_id")
        existing.display_name = result.get("display_name")
        existing.email = result.get("email")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.SALESFORCE,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            instance_url=result.get("instance_url"),
            provider_user_id=result.get("user_id"),
            org_id=result.get("org_id"),
            display_name=result.get("display_name"),
            email=result.get("email"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=salesforce_connected"}
    )


@router.get("/salesforce/status")
async def salesforce_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Salesforce connection status.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE,
        UserIntegration.is_active == True
    ).first()

    return {
        "provider": "salesforce",
        "display_name": "Salesforce",
        "is_configured": is_salesforce_configured(),
        "is_connected": integration is not None,
        "instance_url": integration.instance_url if integration else None,
        "org_id": integration.org_id if integration else None,
        "user_email": integration.email if integration else None,
        "display_name_user": integration.display_name if integration else None,
        "connected_at": integration.connected_at if integration else None,
        "settings": {
            "auto_sync_contacts": integration.auto_sync_contacts if integration else True,
            "auto_log_meetings": integration.auto_log_meetings if integration else True,
            "auto_sync_notes": integration.auto_sync_notes if integration else False,
            "auto_create_tasks": integration.auto_create_tasks if integration else False,
        } if integration else None,
    }


@router.put("/salesforce/settings")
async def update_salesforce_settings(
    settings: SalesforceSyncSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update Salesforce sync settings.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Salesforce not connected")

    integration.auto_sync_contacts = settings.auto_sync_contacts
    integration.auto_log_meetings = settings.auto_log_meetings
    integration.auto_sync_notes = settings.auto_sync_notes
    integration.auto_create_tasks = settings.auto_create_tasks
    integration.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Salesforce settings updated"}


@router.post("/salesforce/sync-meeting")
async def sync_meeting_to_salesforce(
    request: SalesforceMeetingSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually sync a meeting to Salesforce.

    Creates/updates contacts, logs meeting activity, and optionally syncs notes.
    """
    from models import Meeting, MeetingSummary, ActionItem

    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Salesforce not connected")

    # Get meeting
    meeting = db.query(Meeting).filter(
        Meeting.id == request.meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Get summary and action items
    summary = db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).first()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).all() if request.include_action_items else []

    # Prepare participants
    participants = request.participants or []

    salesforce_service = SalesforceService(db)

    # Refresh token if needed (Salesforce tokens don't have standard expiration)
    if integration.refresh_token:
        refresh_result = await salesforce_service.refresh_token(
            integration.refresh_token,
            integration.instance_url
        )
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            db.commit()

    # Sync meeting
    result = await salesforce_service.sync_meeting(
        instance_url=integration.instance_url,
        access_token=integration.access_token,
        meeting_title=meeting.title or "Meeting",
        meeting_date=meeting.started_at,
        duration_minutes=meeting.duration_seconds // 60 if meeting.duration_seconds else 30,
        participants=participants,
        summary=summary.summary_text if summary else None,
        key_points=summary.key_points if summary else None,
        action_items=[
            {
                "description": ai.description,
                "assignee": ai.assignee,
                "assignee_email": None,
                "priority": ai.priority,
                "due_date": ai.due_date,
            }
            for ai in action_items
        ],
        notes=meeting.notes if request.include_notes else None,
    )

    await salesforce_service.close()

    integration.last_used_at = datetime.utcnow()
    db.commit()

    return result


@router.post("/salesforce/find-contact")
async def find_salesforce_contact(
    email: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Find a contact in Salesforce by email.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Salesforce not connected")

    salesforce_service = SalesforceService(db)
    contact = await salesforce_service.find_contact_by_email(
        integration.instance_url,
        integration.access_token,
        email
    )
    await salesforce_service.close()

    if contact:
        return {"found": True, "contact": contact}
    return {"found": False, "contact": None}


@router.delete("/salesforce")
async def disconnect_salesforce(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Salesforce integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.SALESFORCE
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Salesforce disconnected"}


# =============================================================================
# HUBSPOT CRM INTEGRATION
# =============================================================================

from services.hubspot_service import HubSpotService, is_hubspot_configured


class HubSpotSyncSettings(BaseModel):
    """Settings for HubSpot sync."""
    auto_sync_contacts: bool = True
    auto_log_meetings: bool = True
    auto_sync_notes: bool = False
    auto_create_tasks: bool = False


class HubSpotMeetingSyncRequest(BaseModel):
    """Request to sync a meeting to HubSpot."""
    meeting_id: int
    participants: Optional[List[dict]] = None
    include_notes: bool = False
    include_action_items: bool = True


@router.get("/hubspot/authorize")
async def hubspot_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get HubSpot OAuth authorization URL.
    """
    if not is_hubspot_configured():
        raise HTTPException(status_code=503, detail="HubSpot integration not configured")

    hubspot_service = HubSpotService(db)
    redirect_uri = f"{APP_URL}/api/integrations/hubspot/callback"
    auth_url = hubspot_service.get_oauth_url(current_user.id, redirect_uri)

    return {"authorization_url": auth_url}


@router.get("/hubspot/callback")
async def hubspot_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Handle HubSpot OAuth callback.
    """
    if not is_hubspot_configured():
        raise HTTPException(status_code=503, detail="HubSpot integration not configured")

    # Parse state to get user_id
    try:
        parts = state.split(":")
        user_id = int(parts[0])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Exchange code for token
    hubspot_service = HubSpotService(db)
    redirect_uri = f"{APP_URL}/api/integrations/hubspot/callback"
    result = await hubspot_service.exchange_code(code, redirect_uri)
    await hubspot_service.close()

    if not result.get("success"):
        logger.error(f"HubSpot OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=hubspot_auth_failed"}
        )

    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 21600))
        existing.provider_user_id = result.get("user_id")
        existing.org_id = result.get("hub_id")
        existing.provider_team_name = result.get("hub_domain")
        existing.display_name = result.get("display_name")
        existing.is_active = True
        existing.error_message = None
        existing.updated_at = datetime.utcnow()
    else:
        integration = UserIntegration(
            user_id=user_id,
            provider=IntegrationProvider.HUBSPOT,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 21600)),
            provider_user_id=result.get("user_id"),
            org_id=result.get("hub_id"),
            provider_team_name=result.get("hub_domain"),
            display_name=result.get("display_name"),
        )
        db.add(integration)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=hubspot_connected"}
    )


@router.get("/hubspot/status")
async def hubspot_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get HubSpot connection status.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT,
        UserIntegration.is_active == True
    ).first()

    return {
        "provider": "hubspot",
        "display_name": "HubSpot",
        "is_configured": is_hubspot_configured(),
        "is_connected": integration is not None,
        "hub_id": integration.org_id if integration else None,
        "hub_domain": integration.provider_team_name if integration else None,
        "display_name_user": integration.display_name if integration else None,
        "connected_at": integration.connected_at if integration else None,
        "settings": {
            "auto_sync_contacts": integration.auto_sync_contacts if integration else True,
            "auto_log_meetings": integration.auto_log_meetings if integration else True,
            "auto_sync_notes": integration.auto_sync_notes if integration else False,
            "auto_create_tasks": integration.auto_create_tasks if integration else False,
        } if integration else None,
    }


@router.put("/hubspot/settings")
async def update_hubspot_settings(
    settings: HubSpotSyncSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update HubSpot sync settings.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="HubSpot not connected")

    integration.auto_sync_contacts = settings.auto_sync_contacts
    integration.auto_log_meetings = settings.auto_log_meetings
    integration.auto_sync_notes = settings.auto_sync_notes
    integration.auto_create_tasks = settings.auto_create_tasks
    integration.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "HubSpot settings updated"}


@router.post("/hubspot/sync-meeting")
async def sync_meeting_to_hubspot(
    request: HubSpotMeetingSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually sync a meeting to HubSpot.

    Creates/updates contacts, logs meeting engagement, and optionally syncs notes.
    """
    from models import Meeting, MeetingSummary, ActionItem

    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="HubSpot not connected")

    # Get meeting
    meeting = db.query(Meeting).filter(
        Meeting.id == request.meeting_id,
        Meeting.user_id == current_user.id
    ).first()

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Get summary and action items
    summary = db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).first()
    action_items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).all() if request.include_action_items else []

    # Prepare participants
    participants = request.participants or []

    hubspot_service = HubSpotService(db)

    # Refresh token if needed
    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await hubspot_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 21600))
            db.commit()
        else:
            await hubspot_service.close()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    # Sync meeting
    result = await hubspot_service.sync_meeting(
        access_token=integration.access_token,
        meeting_title=meeting.title or "Meeting",
        meeting_date=meeting.started_at,
        duration_minutes=meeting.duration_seconds // 60 if meeting.duration_seconds else 30,
        participants=participants,
        summary=summary.summary_text if summary else None,
        key_points=summary.key_points if summary else None,
        action_items=[
            {
                "description": ai.description,
                "assignee": ai.assignee,
                "assignee_email": None,
                "priority": ai.priority,
                "due_date": ai.due_date,
            }
            for ai in action_items
        ],
        notes=meeting.notes if request.include_notes else None,
    )

    await hubspot_service.close()

    integration.last_used_at = datetime.utcnow()
    db.commit()

    return result


@router.post("/hubspot/find-contact")
async def find_hubspot_contact(
    email: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Find a contact in HubSpot by email.
    """
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT,
        UserIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="HubSpot not connected")

    hubspot_service = HubSpotService(db)

    # Refresh token if needed
    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        refresh_result = await hubspot_service.refresh_token(integration.refresh_token)
        if refresh_result.get("success"):
            integration.access_token = refresh_result.get("access_token")
            integration.refresh_token = refresh_result.get("refresh_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(seconds=refresh_result.get("expires_in", 21600))
            db.commit()

    contact = await hubspot_service.find_contact_by_email(integration.access_token, email)
    await hubspot_service.close()

    if contact:
        return {"found": True, "contact": contact}
    return {"found": False, "contact": None}


@router.delete("/hubspot")
async def disconnect_hubspot(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect HubSpot integration."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.provider == IntegrationProvider.HUBSPOT
    ).first()

    if integration:
        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "HubSpot disconnected"}


# =============================================================================
# CRM INTEGRATION STATUS
# =============================================================================

@router.get("/crm/status")
async def get_crm_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of all CRM integrations.
    """
    integrations = []

    user_integrations = db.query(UserIntegration).filter(
        UserIntegration.user_id == current_user.id,
        UserIntegration.is_active == True
    ).all()

    integration_map = {i.provider: i for i in user_integrations}

    # Salesforce
    sf_int = integration_map.get(IntegrationProvider.SALESFORCE)
    integrations.append({
        "provider": "salesforce",
        "display_name": "Salesforce",
        "is_configured": is_salesforce_configured(),
        "is_connected": sf_int is not None,
        "instance_url": sf_int.instance_url if sf_int else None,
        "email": sf_int.email if sf_int else None,
        "display_name_user": sf_int.display_name if sf_int else None,
        "connected_at": sf_int.connected_at if sf_int else None,
        "settings": {
            "auto_sync_contacts": sf_int.auto_sync_contacts if sf_int else True,
            "auto_log_meetings": sf_int.auto_log_meetings if sf_int else True,
            "auto_sync_notes": sf_int.auto_sync_notes if sf_int else False,
            "auto_create_tasks": sf_int.auto_create_tasks if sf_int else False,
        } if sf_int else None,
    })

    # HubSpot
    hs_int = integration_map.get(IntegrationProvider.HUBSPOT)
    integrations.append({
        "provider": "hubspot",
        "display_name": "HubSpot",
        "is_configured": is_hubspot_configured(),
        "is_connected": hs_int is not None,
        "hub_id": hs_int.org_id if hs_int else None,
        "hub_domain": hs_int.provider_team_name if hs_int else None,
        "display_name_user": hs_int.display_name if hs_int else None,
        "connected_at": hs_int.connected_at if hs_int else None,
        "settings": {
            "auto_sync_contacts": hs_int.auto_sync_contacts if hs_int else True,
            "auto_log_meetings": hs_int.auto_log_meetings if hs_int else True,
            "auto_sync_notes": hs_int.auto_sync_notes if hs_int else False,
            "auto_create_tasks": hs_int.auto_create_tasks if hs_int else False,
        } if hs_int else None,
    })

    return {
        "crm_integrations": integrations,
        "description": (
            "CRM integrations allow ReadIn AI to automatically sync meeting participants as contacts, "
            "log meetings as activities, and create tasks from action items in your CRM."
        )
    }
