"""
Microsoft Teams Integration Service for ReadIn AI.

Provides:
- OAuth 2.0 authentication with Microsoft Graph
- Adaptive Card message posting
- Meeting summary notifications
- Action item reminders
- Channel message delivery
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from config import (
    TEAMS_CLIENT_ID,
    TEAMS_CLIENT_SECRET,
    TEAMS_TENANT_ID,
    APP_URL,
)

logger = logging.getLogger("teams")

# Microsoft Graph API endpoints
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
MS_LOGIN_URL = "https://login.microsoftonline.com"


@dataclass
class TeamsConnection:
    """Represents a connected Teams workspace."""
    tenant_id: str
    access_token: str
    refresh_token: str
    user_id: str
    display_name: str
    default_channel: Optional[str] = None


class TeamsService:
    """
    Microsoft Teams integration service for ReadIn AI.

    Uses Microsoft Graph API to send adaptive cards and notifications.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Microsoft OAuth authorization URL.

        Args:
            user_id: User initiating the connection
            redirect_uri: Callback URL after authorization

        Returns:
            OAuth authorization URL
        """
        tenant = TEAMS_TENANT_ID or "common"

        scopes = [
            "https://graph.microsoft.com/Chat.ReadWrite",
            "https://graph.microsoft.com/ChannelMessage.Send",
            "https://graph.microsoft.com/Team.ReadBasic.All",
            "https://graph.microsoft.com/Channel.ReadBasic.All",
            "https://graph.microsoft.com/User.Read",
            "offline_access",
        ]

        state = f"{user_id}"

        params = {
            "client_id": TEAMS_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_mode": "query",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{MS_LOGIN_URL}/{tenant}/oauth2/v2.0/authorize?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        tenant = TEAMS_TENANT_ID or "common"

        try:
            response = await self.client.post(
                f"{MS_LOGIN_URL}/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": TEAMS_CLIENT_ID,
                    "client_secret": TEAMS_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Teams OAuth error: {data.get('error_description')}")
                return {"success": False, "error": data.get("error_description")}

            # Get user info
            user_info = await self._get_user_info(data.get("access_token"))

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "user_id": user_info.get("id"),
                "display_name": user_info.get("displayName"),
                "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            }

        except Exception as e:
            logger.error(f"Teams OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        tenant = TEAMS_TENANT_ID or "common"

        try:
            response = await self.client.post(
                f"{MS_LOGIN_URL}/{tenant}/oauth2/v2.0/token",
                data={
                    "client_id": TEAMS_CLIENT_ID,
                    "client_secret": TEAMS_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            data = response.json()

            if "error" in data:
                return {"success": False, "error": data.get("error_description")}

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
            }

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user info from Microsoft Graph."""
        try:
            response = await self.client.get(
                f"{GRAPH_API_BASE}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {}

    # =========================================================================
    # MESSAGE SENDING
    # =========================================================================

    async def send_chat_message(
        self,
        access_token: str,
        chat_id: str,
        content: str,
        content_type: str = "html",
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a Teams chat.

        Args:
            access_token: Microsoft Graph access token
            chat_id: Chat ID
            content: Message content (HTML or text)
            content_type: "html" or "text"
            attachments: Optional adaptive card attachments

        Returns:
            API response
        """
        try:
            payload = {
                "body": {
                    "contentType": content_type,
                    "content": content,
                },
            }

            if attachments:
                payload["attachments"] = attachments

            response = await self.client.post(
                f"{GRAPH_API_BASE}/chats/{chat_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Teams message error: {data['error']}")
                return {"success": False, "error": data["error"]}

            return {"success": True, "message_id": data.get("id")}

        except Exception as e:
            logger.error(f"Teams message failed: {e}")
            return {"success": False, "error": str(e)}

    async def send_channel_message(
        self,
        access_token: str,
        team_id: str,
        channel_id: str,
        content: str,
        content_type: str = "html",
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Teams channel."""
        try:
            payload = {
                "body": {
                    "contentType": content_type,
                    "content": content,
                },
            }

            if attachments:
                payload["attachments"] = attachments

            response = await self.client.post(
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            data = response.json()

            if "error" in data:
                return {"success": False, "error": data["error"]}

            return {"success": True, "message_id": data.get("id")}

        except Exception as e:
            logger.error(f"Teams channel message failed: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # CHANNEL/TEAM OPERATIONS
    # =========================================================================

    async def list_teams(self, access_token: str) -> List[Dict]:
        """Get list of teams the user belongs to."""
        try:
            response = await self.client.get(
                f"{GRAPH_API_BASE}/me/joinedTeams",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()

            if "error" in data:
                return []

            return [
                {
                    "id": team["id"],
                    "name": team["displayName"],
                    "description": team.get("description", ""),
                }
                for team in data.get("value", [])
            ]

        except Exception as e:
            logger.error(f"Failed to list teams: {e}")
            return []

    async def list_channels(self, access_token: str, team_id: str) -> List[Dict]:
        """Get list of channels in a team."""
        try:
            response = await self.client.get(
                f"{GRAPH_API_BASE}/teams/{team_id}/channels",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()

            if "error" in data:
                return []

            return [
                {
                    "id": ch["id"],
                    "name": ch["displayName"],
                    "description": ch.get("description", ""),
                    "membership_type": ch.get("membershipType", "standard"),
                }
                for ch in data.get("value", [])
            ]

        except Exception as e:
            logger.error(f"Failed to list channels: {e}")
            return []

    # =========================================================================
    # ADAPTIVE CARD TEMPLATES
    # =========================================================================

    def format_meeting_summary_card(
        self,
        meeting_title: str,
        meeting_date: datetime,
        summary: str,
        key_points: List[str],
        action_items: List[Dict],
        sentiment: str,
        meeting_url: str,
    ) -> Dict:
        """
        Format meeting summary as Teams Adaptive Card.

        Returns:
            Adaptive Card JSON for Teams
        """
        # Sentiment color
        sentiment_color = {
            "positive": "Good",
            "negative": "Attention",
            "neutral": "Default",
            "mixed": "Warning",
        }.get(sentiment, "Default")

        # Build key points
        key_points_items = [
            {"type": "TextBlock", "text": f"• {point}", "wrap": True, "size": "Small"}
            for point in key_points[:5]
        ]

        # Build action items
        action_items_content = [
            {
                "type": "TextBlock",
                "text": f"☐ {item.get('description', 'Task')} ({item.get('priority', 'medium')})",
                "wrap": True,
                "size": "Small",
            }
            for item in action_items[:5]
        ]

        card = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": f"📋 Meeting Summary: {meeting_title}",
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True,
                    },
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"📅 {meeting_date.strftime('%B %d, %Y')}",
                                        "size": "Small",
                                        "color": "Default",
                                    },
                                ],
                            },
                            {
                                "type": "Column",
                                "width": "auto",
                                "items": [
                                    {
                                        "type": "TextBlock",
                                        "text": f"Sentiment: {sentiment.title()}",
                                        "size": "Small",
                                        "color": sentiment_color,
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Summary**",
                        "weight": "Bolder",
                        "spacing": "Medium",
                    },
                    {
                        "type": "TextBlock",
                        "text": summary[:500] + ("..." if len(summary) > 500 else ""),
                        "wrap": True,
                        "size": "Small",
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Key Points**",
                        "weight": "Bolder",
                        "spacing": "Medium",
                    },
                    *key_points_items,
                    {
                        "type": "TextBlock",
                        "text": "**Action Items**",
                        "weight": "Bolder",
                        "spacing": "Medium",
                    },
                    *action_items_content,
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View Full Summary",
                        "url": meeting_url,
                    },
                ],
            },
        }

        return card

    def format_action_item_card(
        self,
        task_description: str,
        due_date: datetime,
        priority: str,
        meeting_title: str,
        task_url: str,
    ) -> Dict:
        """Format action item reminder as Adaptive Card."""
        priority_color = {
            "high": "Attention",
            "medium": "Warning",
            "low": "Good",
        }.get(priority, "Default")

        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "⚡ Action Item Reminder",
                        "weight": "Bolder",
                        "size": "Medium",
                    },
                    {
                        "type": "TextBlock",
                        "text": task_description,
                        "wrap": True,
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "From:", "value": meeting_title},
                            {"title": "Due:", "value": due_date.strftime("%B %d, %Y")},
                            {"title": "Priority:", "value": priority.title()},
                        ],
                    },
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View Details",
                        "url": task_url,
                    },
                ],
            },
        }

    def format_briefing_card(
        self,
        meeting_title: str,
        meeting_time: datetime,
        participants: List[str],
        key_topics: List[str],
        briefing_url: str,
    ) -> Dict:
        """Format pre-meeting briefing as Adaptive Card."""
        participants_text = ", ".join(participants[:5])
        if len(participants) > 5:
            participants_text += f" +{len(participants) - 5} more"

        topics_items = [
            {"type": "TextBlock", "text": f"• {topic}", "wrap": True, "size": "Small"}
            for topic in key_topics[:5]
        ]

        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "📋 Meeting Briefing Ready",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                    {
                        "type": "TextBlock",
                        "text": meeting_title,
                        "weight": "Bolder",
                        "wrap": True,
                    },
                    {
                        "type": "TextBlock",
                        "text": f"🕐 {meeting_time.strftime('%I:%M %p')} today",
                        "size": "Small",
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Participants**",
                        "weight": "Bolder",
                        "spacing": "Medium",
                    },
                    {
                        "type": "TextBlock",
                        "text": participants_text,
                        "wrap": True,
                        "size": "Small",
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Suggested Topics**",
                        "weight": "Bolder",
                        "spacing": "Medium",
                    },
                    *topics_items,
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View Full Briefing",
                        "url": briefing_url,
                    },
                ],
            },
        }

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_teams_configured() -> bool:
    """Check if Teams integration is configured."""
    return bool(TEAMS_CLIENT_ID and TEAMS_CLIENT_SECRET)
