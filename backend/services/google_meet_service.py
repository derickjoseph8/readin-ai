"""
Google Meet Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth 2.0 authentication with Google
- Google Calendar sync for Meet detection
- Meeting schedule information
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    APP_URL,
)

logger = logging.getLogger("google_meet")

# Google API endpoints
GOOGLE_API_BASE = "https://www.googleapis.com"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleMeetService:
    """
    Google Meet integration service for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It syncs Google Calendar to detect Meet links in events.
    Audio capture is done locally by the desktop app.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Google OAuth authorization URL.

        Minimal scopes - only calendar read access for meeting detection.
        """
        scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

        state = f"{user_id}:google_meet:{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            response = await self.client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Google OAuth error: {data.get('error_description')}")
                return {"success": False, "error": data.get("error_description")}

            # Get user info
            user_info = await self._get_user_info(data.get("access_token"))

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "user_id": user_info.get("id"),
                "email": user_info.get("email"),
                "display_name": user_info.get("name"),
            }

        except Exception as e:
            logger.error(f"Google OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        try:
            response = await self.client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
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
                "refresh_token": refresh_token,  # Google doesn't always return new refresh token
                "expires_in": data.get("expires_in"),
            }

        except Exception as e:
            logger.error(f"Google token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user info from Google."""
        try:
            response = await self.client.get(
                f"{GOOGLE_API_BASE}/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Google user info: {e}")
            return {}

    # =========================================================================
    # CALENDAR SYNC FOR MEET DETECTION
    # =========================================================================

    async def get_upcoming_meetings(
        self,
        access_token: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get upcoming Google Meet meetings from calendar.

        Scans calendar events for Google Meet links.
        Used by desktop app to know when to activate.
        """
        try:
            if not from_date:
                from_date = datetime.utcnow()
            if not to_date:
                to_date = from_date + timedelta(days=7)

            params = {
                "timeMin": from_date.isoformat() + "Z",
                "timeMax": to_date.isoformat() + "Z",
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 50,
            }

            response = await self.client.get(
                f"{GOOGLE_CALENDAR_API}/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Google Calendar API error: {data}")
                return []

            meetings = []
            for event in data.get("items", []):
                # Check if event has Google Meet link
                conference_data = event.get("conferenceData", {})
                entry_points = conference_data.get("entryPoints", [])

                meet_link = None
                for entry in entry_points:
                    if entry.get("entryPointType") == "video":
                        meet_link = entry.get("uri")
                        break

                # Also check hangoutLink (older format)
                if not meet_link:
                    meet_link = event.get("hangoutLink")

                if meet_link:
                    start = event.get("start", {})
                    start_time = start.get("dateTime") or start.get("date")

                    end = event.get("end", {})
                    end_time = end.get("dateTime") or end.get("date")

                    # Calculate duration
                    duration = 60  # Default 60 minutes
                    if start_time and end_time:
                        try:
                            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                            duration = int((end_dt - start_dt).total_seconds() / 60)
                        except:
                            pass

                    meetings.append({
                        "id": event.get("id"),
                        "topic": event.get("summary", "Google Meet"),
                        "start_time": start_time,
                        "duration": duration,
                        "join_url": meet_link,
                        "attendees": [
                            a.get("email") for a in event.get("attendees", [])
                        ],
                        "platform": "google_meet",
                    })

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Google Meet meetings: {e}")
            return []

    async def get_meeting_details(
        self,
        access_token: str,
        event_id: str,
    ) -> Optional[Dict]:
        """Get details for a specific calendar event."""
        try:
            response = await self.client.get(
                f"{GOOGLE_CALENDAR_API}/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            event = response.json()

            if "error" in event:
                return None

            conference_data = event.get("conferenceData", {})
            entry_points = conference_data.get("entryPoints", [])

            meet_link = None
            for entry in entry_points:
                if entry.get("entryPointType") == "video":
                    meet_link = entry.get("uri")
                    break

            if not meet_link:
                meet_link = event.get("hangoutLink")

            return {
                "id": event.get("id"),
                "topic": event.get("summary"),
                "description": event.get("description"),
                "start_time": event.get("start", {}).get("dateTime"),
                "end_time": event.get("end", {}).get("dateTime"),
                "join_url": meet_link,
                "organizer": event.get("organizer", {}).get("email"),
                "attendees": [
                    {"email": a.get("email"), "name": a.get("displayName")}
                    for a in event.get("attendees", [])
                ],
                "platform": "google_meet",
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

def is_google_meet_configured() -> bool:
    """Check if Google Meet integration is configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
