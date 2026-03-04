"""
Deep Slack Integration for ReadIn AI using slack-bolt.

Provides:
- Slash commands: /readin summary, /readin actions, /readin meetings
- Interactive buttons for completing actions and viewing details
- Daily digest feature
- Real-time notifications

This module uses slack-bolt for event handling and command processing.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from functools import wraps

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy.orm import Session
from sqlalchemy import desc

from config import (
    SLACK_CLIENT_ID,
    SLACK_CLIENT_SECRET,
    SLACK_SIGNING_SECRET,
    APP_URL,
)
from database import SessionLocal
from models import (
    User, UserIntegration, IntegrationProvider,
    Meeting, MeetingSummary, ActionItem, Commitment
)

logger = logging.getLogger("slack_app")

# Singleton Slack app instance
_slack_app: Optional[AsyncApp] = None


def get_slack_app() -> Optional[AsyncApp]:
    """Get or create the Slack app instance."""
    global _slack_app

    if _slack_app is None and is_slack_app_configured():
        _slack_app = create_slack_app()

    return _slack_app


def is_slack_app_configured() -> bool:
    """Check if Slack app is fully configured."""
    return bool(
        SLACK_CLIENT_ID and
        SLACK_CLIENT_SECRET and
        SLACK_SIGNING_SECRET
    )


def create_slack_app() -> AsyncApp:
    """Create and configure the Slack Bolt app."""
    app = AsyncApp(
        token=None,  # We use per-user tokens
        signing_secret=SLACK_SIGNING_SECRET,
        token_verification_enabled=False,  # We verify manually for multi-workspace
    )

    # Register command handlers
    register_commands(app)

    # Register interaction handlers
    register_interactions(app)

    # Register event handlers
    register_events(app)

    return app


def get_db() -> Session:
    """Get a database session."""
    return SessionLocal()


def get_user_from_slack(db: Session, slack_user_id: str, slack_team_id: str) -> Optional[User]:
    """Look up a ReadIn AI user from their Slack credentials."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.provider == IntegrationProvider.SLACK,
        UserIntegration.provider_user_id == slack_user_id,
        UserIntegration.provider_team_id == slack_team_id,
        UserIntegration.is_active == True
    ).first()

    if integration:
        return db.query(User).filter(User.id == integration.user_id).first()

    return None


def get_user_token(db: Session, user_id: int) -> Optional[str]:
    """Get the Slack access token for a user."""
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == IntegrationProvider.SLACK,
        UserIntegration.is_active == True
    ).first()

    return integration.access_token if integration else None


# =============================================================================
# SLASH COMMANDS
# =============================================================================

def register_commands(app: AsyncApp):
    """Register all slash command handlers."""

    @app.command("/readin")
    async def handle_readin_command(ack, command, respond):
        """
        Handle /readin slash commands.

        Subcommands:
        - summary: Get latest meeting summary
        - actions: Get pending action items
        - meetings: Show recent meetings
        - help: Show help message
        """
        await ack()

        text = command.get("text", "").strip()
        parts = text.split(" ", 1)
        subcommand = parts[0].lower() if parts else "help"
        args = parts[1] if len(parts) > 1 else ""

        slack_user_id = command.get("user_id")
        slack_team_id = command.get("team_id")

        db = get_db()
        try:
            user = get_user_from_slack(db, slack_user_id, slack_team_id)

            if not user:
                await respond({
                    "response_type": "ephemeral",
                    "text": ":warning: Your Slack account is not connected to ReadIn AI. "
                           f"Please connect at {APP_URL}/dashboard/settings"
                })
                return

            if subcommand == "summary":
                await handle_summary_command(db, user, respond, args)
            elif subcommand == "actions":
                await handle_actions_command(db, user, respond, args)
            elif subcommand == "meetings":
                await handle_meetings_command(db, user, respond, args)
            else:
                await handle_help_command(respond)
        finally:
            db.close()


async def handle_summary_command(db: Session, user: User, respond: Callable, args: str):
    """Handle /readin summary command - Get latest meeting summary."""
    # Get the most recent meeting with a summary
    meeting = db.query(Meeting).filter(
        Meeting.user_id == user.id,
        Meeting.status == "ended"
    ).order_by(desc(Meeting.ended_at)).first()

    if not meeting:
        await respond({
            "response_type": "ephemeral",
            "text": ":clipboard: No meetings found. Start a meeting in ReadIn AI to get summaries!"
        })
        return

    summary = db.query(MeetingSummary).filter(
        MeetingSummary.meeting_id == meeting.id
    ).first()

    if not summary:
        await respond({
            "response_type": "ephemeral",
            "text": f":hourglass_flowing_sand: Meeting summary for *{meeting.title or 'Untitled'}* is still being generated."
        })
        return

    # Format key points
    key_points_text = ""
    if summary.key_points:
        key_points_text = "\n".join(f"  - {point}" for point in summary.key_points[:5])

    # Get action items count
    action_count = db.query(ActionItem).filter(
        ActionItem.meeting_id == meeting.id,
        ActionItem.status == "pending"
    ).count()

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":memo: {meeting.title or 'Meeting Summary'}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f":calendar: {meeting.started_at.strftime('%B %d, %Y at %I:%M %p')} | "
                           f":stopwatch: {format_duration(meeting.duration_seconds)}"
                }
            ]
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Summary*\n{summary.summary_text[:800]}{'...' if len(summary.summary_text) > 800 else ''}"
            }
        }
    ]

    if key_points_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Key Points*\n{key_points_text}"
            }
        })

    if action_count > 0:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":pushpin: *{action_count} pending action item{'s' if action_count != 1 else ''}*"
            }
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": ":eyes: View Full Summary",
                        "emoji": True
                    },
                    "url": f"{APP_URL}/meetings/{meeting.id}",
                    "action_id": "view_summary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": ":clipboard: View Actions",
                        "emoji": True
                    },
                    "action_id": "view_actions",
                    "value": str(meeting.id)
                }
            ]
        }
    ])

    await respond({
        "response_type": "ephemeral",
        "blocks": blocks
    })


async def handle_actions_command(db: Session, user: User, respond: Callable, args: str):
    """Handle /readin actions command - Get pending action items."""
    # Get pending action items
    pending_actions = db.query(ActionItem).filter(
        ActionItem.user_id == user.id,
        ActionItem.status == "pending"
    ).order_by(ActionItem.due_date.asc().nullslast()).limit(10).all()

    if not pending_actions:
        await respond({
            "response_type": "ephemeral",
            "text": ":white_check_mark: You have no pending action items. Great job staying on top of things!"
        })
        return

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":pushpin: Pending Action Items ({len(pending_actions)})",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    for i, action in enumerate(pending_actions, 1):
        priority_emoji = {
            "high": ":red_circle:",
            "medium": ":large_orange_circle:",
            "low": ":large_green_circle:"
        }.get(action.priority, ":white_circle:")

        due_text = ""
        if action.due_date:
            if action.due_date < datetime.utcnow():
                due_text = f" | :warning: Overdue"
            else:
                due_text = f" | Due: {action.due_date.strftime('%b %d')}"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{priority_emoji} *{i}.* {action.description[:100]}{due_text}"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: Complete",
                    "emoji": True
                },
                "style": "primary",
                "action_id": "complete_action",
                "value": str(action.id)
            }
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"View all action items at {APP_URL}/dashboard/tasks"
                }
            ]
        }
    ])

    await respond({
        "response_type": "ephemeral",
        "blocks": blocks
    })


async def handle_meetings_command(db: Session, user: User, respond: Callable, args: str):
    """Handle /readin meetings command - Show recent meetings."""
    # Get recent meetings
    meetings = db.query(Meeting).filter(
        Meeting.user_id == user.id
    ).order_by(desc(Meeting.started_at)).limit(5).all()

    if not meetings:
        await respond({
            "response_type": "ephemeral",
            "text": ":calendar: No meetings found. Start using ReadIn AI in your meetings!"
        })
        return

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":calendar: Recent Meetings",
                "emoji": True
            }
        },
        {"type": "divider"}
    ]

    for meeting in meetings:
        status_emoji = ":green_circle:" if meeting.status == "ended" else ":red_circle:"

        # Check for summary
        has_summary = db.query(MeetingSummary).filter(
            MeetingSummary.meeting_id == meeting.id
        ).first() is not None

        summary_text = ":memo: Summary available" if has_summary else ":hourglass: Processing..."
        if meeting.status == "active":
            summary_text = ":movie_camera: In Progress"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{status_emoji} *{meeting.title or 'Untitled Meeting'}*\n"
                       f":calendar: {meeting.started_at.strftime('%b %d, %Y at %I:%M %p')} | "
                       f"{summary_text}"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View",
                    "emoji": True
                },
                "url": f"{APP_URL}/meetings/{meeting.id}",
                "action_id": "view_meeting"
            }
        })

    blocks.extend([
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"View all meetings at {APP_URL}/dashboard/meetings"
                }
            ]
        }
    ])

    await respond({
        "response_type": "ephemeral",
        "blocks": blocks
    })


async def handle_help_command(respond: Callable):
    """Handle /readin help command."""
    await respond({
        "response_type": "ephemeral",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":rocket: ReadIn AI Commands",
                    "emoji": True
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Available Commands:*\n\n"
                           ":memo: `/readin summary` - Get your latest meeting summary\n"
                           ":pushpin: `/readin actions` - View pending action items\n"
                           ":calendar: `/readin meetings` - Show recent meetings\n"
                           ":question: `/readin help` - Show this help message"
                }
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":gear: Manage your integration at {APP_URL}/dashboard/settings"
                    }
                ]
            }
        ]
    })


# =============================================================================
# INTERACTIVE COMPONENTS
# =============================================================================

def register_interactions(app: AsyncApp):
    """Register interactive component handlers."""

    @app.action("complete_action")
    async def handle_complete_action(ack, body, respond):
        """Handle the complete action button click."""
        await ack()

        action_id = int(body["actions"][0]["value"])
        slack_user_id = body["user"]["id"]
        slack_team_id = body["team"]["id"]

        db = get_db()
        try:
            user = get_user_from_slack(db, slack_user_id, slack_team_id)

            if not user:
                await respond({
                    "response_type": "ephemeral",
                    "text": ":warning: Could not verify your account.",
                    "replace_original": False
                })
                return

            # Find and complete the action item
            action_item = db.query(ActionItem).filter(
                ActionItem.id == action_id,
                ActionItem.user_id == user.id
            ).first()

            if not action_item:
                await respond({
                    "response_type": "ephemeral",
                    "text": ":x: Action item not found.",
                    "replace_original": False
                })
                return

            # Update the action item status
            action_item.status = "completed"
            action_item.completed_at = datetime.utcnow()
            db.commit()

            await respond({
                "response_type": "ephemeral",
                "text": f":white_check_mark: Marked as complete: _{action_item.description[:50]}..._",
                "replace_original": False
            })
        finally:
            db.close()

    @app.action("view_actions")
    async def handle_view_actions(ack, body, respond):
        """Handle the view actions button click."""
        await ack()

        meeting_id = int(body["actions"][0]["value"])
        slack_user_id = body["user"]["id"]
        slack_team_id = body["team"]["id"]

        db = get_db()
        try:
            user = get_user_from_slack(db, slack_user_id, slack_team_id)

            if not user:
                return

            # Get action items for this meeting
            actions = db.query(ActionItem).filter(
                ActionItem.meeting_id == meeting_id,
                ActionItem.user_id == user.id
            ).order_by(ActionItem.due_date.asc().nullslast()).all()

            if not actions:
                await respond({
                    "response_type": "ephemeral",
                    "text": ":clipboard: No action items for this meeting.",
                    "replace_original": False
                })
                return

            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": ":pushpin: Action Items",
                        "emoji": True
                    }
                },
                {"type": "divider"}
            ]

            for action in actions:
                status_emoji = ":white_check_mark:" if action.status == "completed" else ":white_large_square:"
                priority_emoji = {
                    "high": ":red_circle:",
                    "medium": ":large_orange_circle:",
                    "low": ":large_green_circle:"
                }.get(action.priority, ":white_circle:")

                action_text = f"{status_emoji} {priority_emoji} {action.description[:80]}"

                if action.status == "completed":
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"~{action_text}~"
                        }
                    })
                else:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": action_text
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Complete"
                            },
                            "style": "primary",
                            "action_id": "complete_action",
                            "value": str(action.id)
                        }
                    })

            await respond({
                "response_type": "ephemeral",
                "blocks": blocks,
                "replace_original": False
            })
        finally:
            db.close()

    @app.action("view_summary")
    async def handle_view_summary(ack, body):
        """Handle the view summary button click - just acknowledge, URL opens in browser."""
        await ack()

    @app.action("view_meeting")
    async def handle_view_meeting(ack, body):
        """Handle the view meeting button click - just acknowledge, URL opens in browser."""
        await ack()


# =============================================================================
# EVENT HANDLERS
# =============================================================================

def register_events(app: AsyncApp):
    """Register Slack event handlers."""

    @app.event("app_home_opened")
    async def handle_app_home_opened(event, client):
        """Handle when user opens the app home tab."""
        user_id = event["user"]

        # Build the home tab view
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":rocket: Welcome to ReadIn AI",
                    "emoji": True
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "ReadIn AI captures and summarizes your meetings, extracts action items, "
                           "and helps you stay on top of your commitments.\n\n"
                           "*Quick Commands:*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":memo: `/readin summary` - Latest meeting summary\n"
                           ":pushpin: `/readin actions` - Pending action items\n"
                           ":calendar: `/readin meetings` - Recent meetings"
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":link: *Useful Links*"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":globe_with_meridians: Dashboard",
                            "emoji": True
                        },
                        "url": APP_URL,
                        "action_id": "open_dashboard"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":gear: Settings",
                            "emoji": True
                        },
                        "url": f"{APP_URL}/dashboard/settings",
                        "action_id": "open_settings"
                    }
                ]
            }
        ]

        try:
            await client.views_publish(
                user_id=user_id,
                view={
                    "type": "home",
                    "blocks": blocks
                }
            )
        except SlackApiError as e:
            logger.error(f"Error publishing home tab: {e}")

    @app.event("app_uninstalled")
    async def handle_app_uninstalled(event, context):
        """Handle when the app is uninstalled from a workspace."""
        team_id = context.get("team_id")
        logger.info(f"App uninstalled from workspace: {team_id}")

        # Deactivate integrations for this workspace
        db = get_db()
        try:
            integrations = db.query(UserIntegration).filter(
                UserIntegration.provider == IntegrationProvider.SLACK,
                UserIntegration.provider_team_id == team_id
            ).all()

            for integration in integrations:
                integration.is_active = False
                integration.updated_at = datetime.utcnow()

            db.commit()
            logger.info(f"Deactivated {len(integrations)} integrations for workspace {team_id}")
        finally:
            db.close()


# =============================================================================
# DAILY DIGEST
# =============================================================================

class SlackDailyDigest:
    """Handles sending daily digest messages to Slack users."""

    def __init__(self):
        self.client = None

    async def send_daily_digest(self, user_id: int, channel_id: Optional[str] = None):
        """
        Send a daily digest to a user via Slack.

        Args:
            user_id: ReadIn AI user ID
            channel_id: Optional specific channel, otherwise uses DM
        """
        db = get_db()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return

            # Get user's Slack integration
            integration = db.query(UserIntegration).filter(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == IntegrationProvider.SLACK,
                UserIntegration.is_active == True
            ).first()

            if not integration:
                return

            # Create client with user's token
            client = AsyncWebClient(token=integration.access_token)

            # Get yesterday's summary
            yesterday = datetime.utcnow() - timedelta(days=1)
            today = datetime.utcnow()

            # Count meetings
            meetings_count = db.query(Meeting).filter(
                Meeting.user_id == user_id,
                Meeting.started_at >= yesterday,
                Meeting.started_at < today
            ).count()

            # Count completed actions
            completed_actions = db.query(ActionItem).filter(
                ActionItem.user_id == user_id,
                ActionItem.completed_at >= yesterday,
                ActionItem.completed_at < today
            ).count()

            # Get pending actions
            pending_actions = db.query(ActionItem).filter(
                ActionItem.user_id == user_id,
                ActionItem.status == "pending"
            ).count()

            # Get overdue items
            overdue_count = db.query(ActionItem).filter(
                ActionItem.user_id == user_id,
                ActionItem.status == "pending",
                ActionItem.due_date < today
            ).count()

            # Get upcoming commitments (next 7 days)
            upcoming_commitments = db.query(Commitment).filter(
                Commitment.user_id == user_id,
                Commitment.status == "pending",
                Commitment.due_date >= today,
                Commitment.due_date <= today + timedelta(days=7)
            ).count()

            # Build digest blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":sunrise: Good morning, {user.full_name or 'there'}!",
                        "emoji": True
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":calendar: {today.strftime('%A, %B %d, %Y')}"
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*:chart_with_upwards_trend: Yesterday's Activity*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f":movie_camera: *{meetings_count}* meeting{'s' if meetings_count != 1 else ''}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f":white_check_mark: *{completed_actions}* action{'s' if completed_actions != 1 else ''} completed"
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*:pushpin: Today's Focus*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f":clipboard: *{pending_actions}* pending action{'s' if pending_actions != 1 else ''}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f":handshake: *{upcoming_commitments}* upcoming commitment{'s' if upcoming_commitments != 1 else ''}"
                        }
                    ]
                }
            ]

            if overdue_count > 0:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":warning: *{overdue_count} overdue item{'s' if overdue_count != 1 else ''}* - "
                               f"use `/readin actions` to view"
                    }
                })

            blocks.extend([
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": ":rocket: Open Dashboard",
                                "emoji": True
                            },
                            "url": APP_URL,
                            "action_id": "open_dashboard"
                        }
                    ]
                }
            ])

            # Send the message
            target_channel = channel_id or integration.provider_user_id

            await client.chat_postMessage(
                channel=target_channel,
                text=f"Good morning, {user.full_name}! Here's your daily digest.",
                blocks=blocks
            )

            logger.info(f"Sent daily digest to user {user_id}")

        except SlackApiError as e:
            logger.error(f"Failed to send daily digest: {e}")
        except Exception as e:
            logger.error(f"Error in daily digest: {e}")
        finally:
            db.close()

    async def send_all_daily_digests(self):
        """Send daily digests to all connected Slack users."""
        db = get_db()
        try:
            # Get all active Slack integrations
            integrations = db.query(UserIntegration).filter(
                UserIntegration.provider == IntegrationProvider.SLACK,
                UserIntegration.is_active == True,
                UserIntegration.notifications_enabled == True
            ).all()

            for integration in integrations:
                try:
                    await self.send_daily_digest(integration.user_id)
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.error(f"Failed digest for user {integration.user_id}: {e}")

            logger.info(f"Sent {len(integrations)} daily digests")
        finally:
            db.close()


# =============================================================================
# NOTIFICATION HELPERS
# =============================================================================

async def send_meeting_summary_notification(
    user_id: int,
    meeting_id: int,
    summary_text: str,
    key_points: List[str],
    action_count: int
):
    """Send a meeting summary notification to Slack."""
    db = get_db()
    try:
        integration = db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.provider == IntegrationProvider.SLACK,
            UserIntegration.is_active == True,
            UserIntegration.meeting_summaries_enabled == True
        ).first()

        if not integration:
            return

        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return

        client = AsyncWebClient(token=integration.access_token)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f":memo: Meeting Summary Ready",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{meeting.title or 'Untitled Meeting'}*\n"
                           f":calendar: {meeting.started_at.strftime('%B %d at %I:%M %p')}"
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary_text[:500] + ("..." if len(summary_text) > 500 else "")
                }
            }
        ]

        if key_points:
            points_text = "\n".join(f"- {p}" for p in key_points[:3])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Points:*\n{points_text}"
                }
            })

        if action_count > 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":pushpin: *{action_count} action item{'s' if action_count != 1 else ''}* extracted"
                }
            })

        blocks.extend([
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Full Summary",
                            "emoji": True
                        },
                        "url": f"{APP_URL}/meetings/{meeting_id}",
                        "action_id": "view_summary"
                    }
                ]
            }
        ])

        # Send to user's DM or default channel
        channel = integration.default_channel_id or integration.provider_user_id

        await client.chat_postMessage(
            channel=channel,
            text=f"Meeting summary ready: {meeting.title}",
            blocks=blocks
        )

    except SlackApiError as e:
        logger.error(f"Failed to send meeting notification: {e}")
    except Exception as e:
        logger.error(f"Error sending meeting notification: {e}")
    finally:
        db.close()


async def send_action_item_reminder(
    user_id: int,
    action_item_id: int
):
    """Send an action item reminder to Slack."""
    db = get_db()
    try:
        integration = db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.provider == IntegrationProvider.SLACK,
            UserIntegration.is_active == True,
            UserIntegration.action_item_reminders_enabled == True
        ).first()

        if not integration:
            return

        action_item = db.query(ActionItem).filter(
            ActionItem.id == action_item_id
        ).first()

        if not action_item:
            return

        meeting = db.query(Meeting).filter(Meeting.id == action_item.meeting_id).first()

        client = AsyncWebClient(token=integration.access_token)

        priority_emoji = {
            "high": ":red_circle:",
            "medium": ":large_orange_circle:",
            "low": ":large_green_circle:"
        }.get(action_item.priority, ":white_circle:")

        due_text = ""
        if action_item.due_date:
            if action_item.due_date < datetime.utcnow():
                due_text = ":warning: *Overdue*"
            elif action_item.due_date.date() == datetime.utcnow().date():
                due_text = ":clock1: *Due today*"
            else:
                due_text = f":calendar: Due {action_item.due_date.strftime('%b %d')}"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{priority_emoji} *Action Item Reminder*\n\n{action_item.description}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":memo: From: {meeting.title if meeting else 'Meeting'} | {due_text}"
                    }
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":white_check_mark: Mark Complete",
                            "emoji": True
                        },
                        "style": "primary",
                        "action_id": "complete_action",
                        "value": str(action_item.id)
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details",
                            "emoji": True
                        },
                        "url": f"{APP_URL}/dashboard/tasks",
                        "action_id": "view_action_details"
                    }
                ]
            }
        ]

        channel = integration.default_channel_id or integration.provider_user_id

        await client.chat_postMessage(
            channel=channel,
            text=f"Reminder: {action_item.description[:50]}...",
            blocks=blocks
        )

    except SlackApiError as e:
        logger.error(f"Failed to send reminder: {e}")
    except Exception as e:
        logger.error(f"Error sending reminder: {e}")
    finally:
        db.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds to human-readable string."""
    if not seconds:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


# Create handler for FastAPI integration
def create_slack_handler():
    """Create FastAPI handler for Slack events."""
    app = get_slack_app()
    if app:
        return AsyncSlackRequestHandler(app)
    return None
