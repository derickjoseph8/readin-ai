"""
Integration routes for Slack and Microsoft Teams.

Provides:
- OAuth authorization flows
- Token management
- Integration settings
- Notification delivery
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserIntegration, IntegrationProvider
from auth import get_current_user
from services.slack_service import SlackService, is_slack_configured
from services.teams_service import TeamsService, is_teams_configured
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
