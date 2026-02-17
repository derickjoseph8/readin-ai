"""
Cisco Webex Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth 2.0 authentication with Webex
- Meeting schedule sync
- Meeting detection
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

from config import (
    WEBEX_CLIENT_ID,
    WEBEX_CLIENT_SECRET,
    APP_URL,
)

logger = logging.getLogger("webex")

# Webex API endpoints
WEBEX_API_BASE = "https://webexapis.com/v1"
WEBEX_AUTH_URL = "https://webexapis.com/v1/authorize"
WEBEX_TOKEN_URL = "https://webexapis.com/v1/access_token"


class WebexService:
    """
    Cisco Webex integration service for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It syncs meeting schedules for the desktop app to detect.
    Audio capture is done locally - completely invisible.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Webex OAuth authorization URL.

        Minimal scopes for meeting schedule access only.
        """
        scopes = [
            "meeting:schedules_read",
            "spark:people_read",
        ]

        state = f"{user_id}:webex:{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": WEBEX_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{WEBEX_AUTH_URL}?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            response = await self.client.post(
                WEBEX_TOKEN_URL,
                data={
                    "client_id": WEBEX_CLIENT_ID,
                    "client_secret": WEBEX_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Webex OAuth error: {data.get('error_description')}")
                return {"success": False, "error": data.get("error_description")}

            # Get user info
            user_info = await self._get_user_info(data.get("access_token"))

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "user_id": user_info.get("id"),
                "email": user_info.get("emails", [None])[0],
                "display_name": user_info.get("displayName"),
            }

        except Exception as e:
            logger.error(f"Webex OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        try:
            response = await self.client.post(
                WEBEX_TOKEN_URL,
                data={
                    "client_id": WEBEX_CLIENT_ID,
                    "client_secret": WEBEX_CLIENT_SECRET,
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
            logger.error(f"Webex token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user info from Webex."""
        try:
            response = await self.client.get(
                f"{WEBEX_API_BASE}/people/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Webex user info: {e}")
            return {}

    # =========================================================================
    # MEETING SCHEDULE SYNC
    # =========================================================================

    async def get_upcoming_meetings(
        self,
        access_token: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get upcoming Webex meetings.

        Used by desktop app for meeting detection.
        Does NOT join meetings.
        """
        try:
            if not from_date:
                from_date = datetime.utcnow()
            if not to_date:
                to_date = from_date + timedelta(days=7)

            params = {
                "from": from_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "to": to_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "max": 50,
            }

            response = await self.client.get(
                f"{WEBEX_API_BASE}/meetings",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "errors" in data:
                logger.error(f"Webex API error: {data}")
                return []

            meetings = []
            for meeting in data.get("items", []):
                start_time = meeting.get("start")
                end_time = meeting.get("end")

                # Calculate duration
                duration = 60
                if start_time and end_time:
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                        duration = int((end_dt - start_dt).total_seconds() / 60)
                    except:
                        pass

                meetings.append({
                    "id": meeting.get("id"),
                    "topic": meeting.get("title", "Webex Meeting"),
                    "start_time": start_time,
                    "duration": duration,
                    "join_url": meeting.get("webLink"),
                    "meeting_number": meeting.get("meetingNumber"),
                    "password": meeting.get("password"),  # Some meetings have passwords
                    "platform": "webex",
                })

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Webex meetings: {e}")
            return []

    async def get_meeting_details(
        self,
        access_token: str,
        meeting_id: str,
    ) -> Optional[Dict]:
        """Get details for a specific meeting."""
        try:
            response = await self.client.get(
                f"{WEBEX_API_BASE}/meetings/{meeting_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            meeting = response.json()

            if "errors" in meeting:
                return None

            return {
                "id": meeting.get("id"),
                "topic": meeting.get("title"),
                "agenda": meeting.get("agenda"),
                "start_time": meeting.get("start"),
                "end_time": meeting.get("end"),
                "join_url": meeting.get("webLink"),
                "host_email": meeting.get("hostEmail"),
                "meeting_number": meeting.get("meetingNumber"),
                "platform": "webex",
            }

        except Exception as e:
            logger.error(f"Failed to get meeting details: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_webex_configured() -> bool:
    """Check if Webex integration is configured."""
    return bool(WEBEX_CLIENT_ID and WEBEX_CLIENT_SECRET)
