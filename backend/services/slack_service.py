"""
Slack Integration Service for ReadIn AI.

Provides:
- OAuth 2.0 authentication with Slack
- Channel message posting
- Meeting summary notifications
- Action item reminders
- Real-time meeting alerts
- Slash command handling
"""

import logging
import hmac
import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import httpx
from sqlalchemy.orm import Session

from config import (
    SLACK_CLIENT_ID,
    SLACK_CLIENT_SECRET,
    SLACK_SIGNING_SECRET,
    APP_URL,
)

logger = logging.getLogger("slack")

# Slack API endpoints
SLACK_API_BASE = "https://slack.com/api"
SLACK_OAUTH_URL = "https://slack.com/oauth/v2/authorize"
SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"


class SlackMessageType(str, Enum):
    """Types of Slack messages."""
    MEETING_SUMMARY = "meeting_summary"
    ACTION_ITEM = "action_item"
    BRIEFING = "briefing"
    REMINDER = "reminder"
    ALERT = "alert"


@dataclass
class SlackWorkspace:
    """Represents a connected Slack workspace."""
    team_id: str
    team_name: str
    access_token: str
    bot_user_id: str
    default_channel: Optional[str] = None


class SlackService:
    """
    Slack integration service for ReadIn AI.

    Handles OAuth, message formatting, and delivery to Slack workspaces.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Slack OAuth authorization URL.

        Args:
            user_id: User initiating the connection
            redirect_uri: Callback URL after authorization

        Returns:
            OAuth authorization URL
        """
        scopes = [
            "chat:write",
            "channels:read",
            "groups:read",
            "im:write",
            "users:read",
            "commands",
        ]

        state = f"{user_id}:{int(time.time())}"

        params = {
            "client_id": SLACK_CLIENT_ID,
            "scope": ",".join(scopes),
            "redirect_uri": redirect_uri,
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{SLACK_OAUTH_URL}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Token response with access_token, team info, etc.
        """
        try:
            response = await self.client.post(
                SLACK_TOKEN_URL,
                data={
                    "client_id": SLACK_CLIENT_ID,
                    "client_secret": SLACK_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            data = response.json()

            if not data.get("ok"):
                logger.error(f"Slack OAuth error: {data.get('error')}")
                return {"success": False, "error": data.get("error")}

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "team_id": data.get("team", {}).get("id"),
                "team_name": data.get("team", {}).get("name"),
                "bot_user_id": data.get("bot_user_id"),
                "authed_user": data.get("authed_user", {}),
            }

        except Exception as e:
            logger.error(f"Slack OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MESSAGE SENDING
    # =========================================================================

    async def send_message(
        self,
        access_token: str,
        channel: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Slack channel.

        Args:
            access_token: Slack bot access token
            channel: Channel ID or name
            text: Fallback text for notifications
            blocks: Rich message blocks (Block Kit format)
            thread_ts: Thread timestamp for replies

        Returns:
            Slack API response
        """
        try:
            payload = {
                "channel": channel,
                "text": text,
            }

            if blocks:
                payload["blocks"] = blocks

            if thread_ts:
                payload["thread_ts"] = thread_ts

            response = await self.client.post(
                f"{SLACK_API_BASE}/chat.postMessage",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )

            data = response.json()

            if not data.get("ok"):
                logger.error(f"Slack message error: {data.get('error')}")
                return {"success": False, "error": data.get("error")}

            return {
                "success": True,
                "ts": data.get("ts"),
                "channel": data.get("channel"),
            }

        except Exception as e:
            logger.error(f"Slack message failed: {e}")
            return {"success": False, "error": str(e)}

    async def update_message(
        self,
        access_token: str,
        channel: str,
        ts: str,
        text: str,
        blocks: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Update an existing Slack message."""
        try:
            payload = {
                "channel": channel,
                "ts": ts,
                "text": text,
            }

            if blocks:
                payload["blocks"] = blocks

            response = await self.client.post(
                f"{SLACK_API_BASE}/chat.update",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
            )

            return response.json()

        except Exception as e:
            logger.error(f"Slack update failed: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # CHANNEL OPERATIONS
    # =========================================================================

    async def list_channels(self, access_token: str) -> List[Dict]:
        """Get list of channels the bot can access."""
        try:
            channels = []
            cursor = None

            while True:
                params = {"limit": 100, "types": "public_channel,private_channel"}
                if cursor:
                    params["cursor"] = cursor

                response = await self.client.get(
                    f"{SLACK_API_BASE}/conversations.list",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )

                data = response.json()

                if not data.get("ok"):
                    break

                channels.extend(data.get("channels", []))

                cursor = data.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            return [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "is_private": ch.get("is_private", False),
                    "is_member": ch.get("is_member", False),
                }
                for ch in channels
            ]

        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []

    # =========================================================================
    # MESSAGE TEMPLATES
    # =========================================================================

    def format_meeting_summary(
        self,
        meeting_title: str,
        meeting_date: datetime,
        summary: str,
        key_points: List[str],
        action_items: List[Dict],
        sentiment: str,
        meeting_url: str,
    ) -> List[Dict]:
        """
        Format meeting summary as Slack Block Kit message.

        Returns:
            List of Slack blocks for rich formatting
        """
        # Sentiment emoji
        sentiment_emoji = {
            "positive": ":white_check_mark:",
            "negative": ":warning:",
            "neutral": ":grey_question:",
            "mixed": ":scales:",
        }.get(sentiment, ":grey_question:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📋 Meeting Summary: {meeting_title}",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📅 {meeting_date.strftime('%B %d, %Y at %I:%M %p')} | {sentiment_emoji} {sentiment.title()} sentiment",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary*\n{summary[:500]}{'...' if len(summary) > 500 else ''}",
                },
            },
        ]

        # Key points
        if key_points:
            points_text = "\n".join(f"• {point}" for point in key_points[:5])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Key Points*\n{points_text}",
                },
            })

        # Action items
        if action_items:
            actions_text = "\n".join(
                f"• {item.get('description', 'Task')} ({item.get('priority', 'medium')} priority)"
                for item in action_items[:5]
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Action Items*\n{actions_text}",
                },
            })

        # View full summary button
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
                            "emoji": True,
                        },
                        "url": meeting_url,
                        "action_id": "view_summary",
                    },
                ],
            },
        ])

        return blocks

    def format_action_item_reminder(
        self,
        task_description: str,
        due_date: datetime,
        priority: str,
        meeting_title: str,
        task_url: str,
    ) -> List[Dict]:
        """Format action item reminder as Slack blocks."""
        priority_emoji = {
            "high": ":red_circle:",
            "medium": ":large_orange_circle:",
            "low": ":large_green_circle:",
        }.get(priority, ":white_circle:")

        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{priority_emoji} Action Item Reminder*\n{task_description}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"From: _{meeting_title}_ | Due: *{due_date.strftime('%B %d')}*",
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Mark Complete",
                        },
                        "style": "primary",
                        "action_id": "complete_action",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details",
                        },
                        "url": task_url,
                        "action_id": "view_action",
                    },
                ],
            },
        ]

    def format_briefing_notification(
        self,
        meeting_title: str,
        meeting_time: datetime,
        participants: List[str],
        key_topics: List[str],
        briefing_url: str,
    ) -> List[Dict]:
        """Format pre-meeting briefing notification."""
        participants_text = ", ".join(participants[:5])
        if len(participants) > 5:
            participants_text += f" +{len(participants) - 5} more"

        topics_text = "\n".join(f"• {topic}" for topic in key_topics[:5])

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Meeting Briefing Ready",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{meeting_title}*\n🕐 {meeting_time.strftime('%I:%M %p')} today",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Participants*\n{participants_text}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggested Topics*\n{topics_text}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Full Briefing",
                        },
                        "style": "primary",
                        "url": briefing_url,
                        "action_id": "view_briefing",
                    },
                ],
            },
        ]

    # =========================================================================
    # WEBHOOK VERIFICATION
    # =========================================================================

    def verify_request(self, timestamp: str, signature: str, body: bytes) -> bool:
        """
        Verify incoming Slack webhook request.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header
            body: Raw request body

        Returns:
            True if signature is valid
        """
        if not SLACK_SIGNING_SECRET:
            logger.warning("Slack signing secret not configured")
            return False

        # Check timestamp to prevent replay attacks
        try:
            request_time = int(timestamp)
            if abs(time.time() - request_time) > 300:  # 5 minutes
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

    # =========================================================================
    # SLASH COMMANDS
    # =========================================================================

    async def handle_slash_command(
        self,
        command: str,
        text: str,
        user_id: str,
        channel_id: str,
        response_url: str,
    ) -> Dict[str, Any]:
        """
        Handle Slack slash commands.

        Supported commands:
        - /readin summary - Get latest meeting summary
        - /readin upcoming - List upcoming meetings
        - /readin actions - List pending action items
        - /readin help - Show help
        """
        parts = text.strip().split(" ", 1)
        subcommand = parts[0].lower() if parts else "help"

        if subcommand == "summary":
            return {
                "response_type": "ephemeral",
                "text": "Fetching your latest meeting summary...",
                # This would trigger an async job to fetch and post the summary
            }

        elif subcommand == "upcoming":
            return {
                "response_type": "ephemeral",
                "text": "Fetching your upcoming meetings...",
            }

        elif subcommand == "actions":
            return {
                "response_type": "ephemeral",
                "text": "Fetching your pending action items...",
            }

        else:  # help
            return {
                "response_type": "ephemeral",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*ReadIn AI Slack Commands*",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": (
                                "`/readin summary` - Get your latest meeting summary\n"
                                "`/readin upcoming` - List upcoming meetings\n"
                                "`/readin actions` - List pending action items\n"
                                "`/readin help` - Show this help message"
                            ),
                        },
                    },
                ],
            }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_slack_configured() -> bool:
    """Check if Slack integration is configured."""
    return bool(SLACK_CLIENT_ID and SLACK_CLIENT_SECRET)
