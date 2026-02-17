"""
Zoom Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth 2.0 authentication with Zoom
- Calendar/meeting schedule sync
- Meeting detection (start/end events)
- User profile information
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from config import (
    ZOOM_CLIENT_ID,
    ZOOM_CLIENT_SECRET,
    APP_URL,
)

logger = logging.getLogger("zoom")

# Zoom API endpoints
ZOOM_API_BASE = "https://api.zoom.us/v2"
ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"


@dataclass
class ZoomMeeting:
    """Represents a Zoom meeting."""
    id: str
    topic: str
    start_time: datetime
    duration: int  # minutes
    join_url: str
    host_id: str
    status: str  # waiting, started, ended


class ZoomService:
    """
    Zoom integration service for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It only syncs calendar data to help the desktop app know when
    meetings are happening. Audio capture is done locally.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Zoom OAuth authorization URL.

        Scopes requested are minimal - only what's needed for calendar sync.
        No recording or participant access requested.
        """
        scopes = [
            "user:read",           # Basic user info
            "meeting:read",        # Read meeting schedules
        ]

        state = f"{user_id}:{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": ZOOM_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{ZOOM_AUTH_URL}?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            import base64

            # Zoom requires Basic auth for token exchange
            credentials = base64.b64encode(
                f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()
            ).decode()

            response = await self.client.post(
                ZOOM_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Zoom OAuth error: {data.get('error_description')}")
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
                "display_name": f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip(),
            }

        except Exception as e:
            logger.error(f"Zoom OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        try:
            import base64

            credentials = base64.b64encode(
                f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()
            ).decode()

            response = await self.client.post(
                ZOOM_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
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
            logger.error(f"Zoom token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user info from Zoom."""
        try:
            response = await self.client.get(
                f"{ZOOM_API_BASE}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Zoom user info: {e}")
            return {}

    # =========================================================================
    # MEETING SCHEDULE SYNC (For meeting detection only)
    # =========================================================================

    async def get_upcoming_meetings(
        self,
        access_token: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get user's upcoming Zoom meetings.

        Used by desktop app to know when to activate for meetings.
        Does NOT join meetings - just provides schedule info.
        """
        try:
            params = {"type": "upcoming", "page_size": 30}

            response = await self.client.get(
                f"{ZOOM_API_BASE}/users/me/meetings",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Zoom API error: {data}")
                return []

            meetings = []
            for meeting in data.get("meetings", []):
                start_time = meeting.get("start_time")
                if start_time:
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                else:
                    start_dt = None

                meetings.append({
                    "id": str(meeting.get("id")),
                    "topic": meeting.get("topic", "Zoom Meeting"),
                    "start_time": start_dt.isoformat() if start_dt else None,
                    "duration": meeting.get("duration", 0),
                    "join_url": meeting.get("join_url"),
                    "meeting_type": self._get_meeting_type(meeting.get("type")),
                    "platform": "zoom",
                })

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Zoom meetings: {e}")
            return []

    async def get_meeting_details(
        self,
        access_token: str,
        meeting_id: str,
    ) -> Optional[Dict]:
        """Get details for a specific meeting."""
        try:
            response = await self.client.get(
                f"{ZOOM_API_BASE}/meetings/{meeting_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()

            if "error" in data:
                return None

            return {
                "id": str(data.get("id")),
                "topic": data.get("topic"),
                "start_time": data.get("start_time"),
                "duration": data.get("duration"),
                "host_email": data.get("host_email"),
                "join_url": data.get("join_url"),
                "status": data.get("status"),
                "platform": "zoom",
            }

        except Exception as e:
            logger.error(f"Failed to get meeting details: {e}")
            return None

    def _get_meeting_type(self, type_code: int) -> str:
        """Convert Zoom meeting type code to string."""
        types = {
            1: "instant",
            2: "scheduled",
            3: "recurring_no_fixed",
            8: "recurring_fixed",
        }
        return types.get(type_code, "unknown")

    # =========================================================================
    # MEETING DETECTION HELPERS (For desktop app)
    # =========================================================================

    async def check_active_meeting(
        self,
        access_token: str,
    ) -> Optional[Dict]:
        """
        Check if user is currently in a meeting.

        Used by desktop app to detect meeting state.
        """
        try:
            # Get user's current meeting status
            response = await self.client.get(
                f"{ZOOM_API_BASE}/users/me/meetings",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"type": "live"},
            )

            data = response.json()
            meetings = data.get("meetings", [])

            if meetings:
                meeting = meetings[0]
                return {
                    "id": str(meeting.get("id")),
                    "topic": meeting.get("topic"),
                    "start_time": meeting.get("start_time"),
                    "is_active": True,
                    "platform": "zoom",
                }

            return None

        except Exception as e:
            logger.error(f"Failed to check active meeting: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_zoom_configured() -> bool:
    """Check if Zoom integration is configured."""
    return bool(ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET)
