"""
Microsoft Teams Meeting Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

This is separate from teams_service.py which handles MESSAGING.
This service handles MEETINGS/VIDEO CALLS detection.

Provides:
- Meeting schedule sync via Microsoft Graph Calendar API
- Teams meeting detection
- Meeting details retrieval
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

from config import (
    TEAMS_CLIENT_ID,
    TEAMS_CLIENT_SECRET,
    TEAMS_TENANT_ID,
    APP_URL,
)

logger = logging.getLogger("teams_meeting")

# Microsoft Graph API endpoints
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
MS_LOGIN_URL = "https://login.microsoftonline.com"


class TeamsMeetingService:
    """
    Microsoft Teams Meeting integration for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It syncs calendar to detect Teams meeting links.
    Audio capture is done locally by the desktop app.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW (Uses same as teams_service but with calendar scopes)
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Microsoft OAuth authorization URL for calendar access.

        Minimal scopes - only calendar read for meeting detection.
        """
        tenant = TEAMS_TENANT_ID or "common"

        scopes = [
            "https://graph.microsoft.com/Calendars.Read",
            "https://graph.microsoft.com/User.Read",
            "offline_access",
        ]

        state = f"{user_id}:teams_meeting:{int(datetime.utcnow().timestamp())}"

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
        """Exchange authorization code for access token."""
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
                "email": user_info.get("mail") or user_info.get("userPrincipalName"),
                "display_name": user_info.get("displayName"),
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
    # CALENDAR SYNC FOR TEAMS MEETING DETECTION
    # =========================================================================

    async def get_upcoming_meetings(
        self,
        access_token: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get upcoming Teams meetings from calendar.

        Scans calendar events for Teams meeting links.
        Used by desktop app for meeting detection.
        """
        try:
            if not from_date:
                from_date = datetime.utcnow()
            if not to_date:
                to_date = from_date + timedelta(days=7)

            # Microsoft Graph calendar query
            params = {
                "startDateTime": from_date.isoformat() + "Z",
                "endDateTime": to_date.isoformat() + "Z",
                "$orderby": "start/dateTime",
                "$top": 50,
                "$select": "subject,start,end,onlineMeeting,onlineMeetingUrl,isOnlineMeeting,organizer,attendees",
            }

            response = await self.client.get(
                f"{GRAPH_API_BASE}/me/calendarView",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Graph API error: {data}")
                return []

            meetings = []
            for event in data.get("value", []):
                # Check if it's a Teams meeting
                is_teams = event.get("isOnlineMeeting", False)
                meeting_url = event.get("onlineMeetingUrl")

                # Also check onlineMeeting object
                online_meeting = event.get("onlineMeeting", {})
                if online_meeting:
                    meeting_url = meeting_url or online_meeting.get("joinUrl")

                if is_teams or (meeting_url and "teams" in meeting_url.lower()):
                    start = event.get("start", {})
                    end = event.get("end", {})

                    start_time = start.get("dateTime")
                    end_time = end.get("dateTime")

                    # Calculate duration
                    duration = 60
                    if start_time and end_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time)
                            end_dt = datetime.fromisoformat(end_time)
                            duration = int((end_dt - start_dt).total_seconds() / 60)
                        except:
                            pass

                    meetings.append({
                        "id": event.get("id"),
                        "topic": event.get("subject", "Teams Meeting"),
                        "start_time": start_time,
                        "duration": duration,
                        "join_url": meeting_url,
                        "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address"),
                        "attendees": [
                            a.get("emailAddress", {}).get("address")
                            for a in event.get("attendees", [])
                        ],
                        "platform": "microsoft_teams",
                    })

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Teams meetings: {e}")
            return []

    async def get_meeting_details(
        self,
        access_token: str,
        event_id: str,
    ) -> Optional[Dict]:
        """Get details for a specific calendar event."""
        try:
            response = await self.client.get(
                f"{GRAPH_API_BASE}/me/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            event = response.json()

            if "error" in event:
                return None

            return {
                "id": event.get("id"),
                "topic": event.get("subject"),
                "body": event.get("body", {}).get("content"),
                "start_time": event.get("start", {}).get("dateTime"),
                "end_time": event.get("end", {}).get("dateTime"),
                "join_url": event.get("onlineMeetingUrl"),
                "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address"),
                "attendees": [
                    {
                        "email": a.get("emailAddress", {}).get("address"),
                        "name": a.get("emailAddress", {}).get("name"),
                    }
                    for a in event.get("attendees", [])
                ],
                "platform": "microsoft_teams",
            }

        except Exception as e:
            logger.error(f"Failed to get event details: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_teams_meeting_configured() -> bool:
    """Check if Teams meeting integration is configured."""
    return bool(TEAMS_CLIENT_ID and TEAMS_CLIENT_SECRET)
