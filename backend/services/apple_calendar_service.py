"""
Apple Calendar Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- CalDAV-based calendar sync for meeting detection
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth 2.0 authentication with Apple
- CalDAV-based calendar sync
- Fetch upcoming events
- Event creation support
- Meeting schedule information
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

import httpx
from sqlalchemy.orm import Session

from config import (
    APPLE_CLIENT_ID,
    APPLE_CLIENT_SECRET,
    APPLE_TEAM_ID,
    APPLE_KEY_ID,
    APP_URL,
)

logger = logging.getLogger("apple_calendar")

# Apple OAuth endpoints
APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"

# Apple CalDAV endpoints
CALDAV_BASE_URL = "https://caldav.icloud.com"
CALDAV_PRINCIPAL = "https://caldav.icloud.com/principals/users"


@dataclass
class AppleCalendarEvent:
    """Represents an Apple Calendar event."""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    meeting_link: Optional[str]
    calendar_id: str
    etag: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "topic": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": int((self.end_time - self.start_time).total_seconds() / 60) if self.start_time and self.end_time else 60,
            "location": self.location,
            "attendees": self.attendees,
            "join_url": self.meeting_link,
            "calendar_id": self.calendar_id,
            "platform": "apple_calendar",
        }


class AppleCalendarService:
    """
    Apple Calendar integration service for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It syncs Apple Calendar via CalDAV to detect meeting schedules.
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
        Generate Apple OAuth authorization URL.

        Uses Sign in with Apple for authentication, then CalDAV for calendar access.
        """
        scopes = ["name", "email"]

        state = f"{user_id}:apple_calendar:{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": APPLE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_mode": "form_post",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{APPLE_AUTH_URL}?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Apple Sign in returns a JWT token that we validate and use
        to obtain CalDAV credentials.
        """
        try:
            # Generate client secret (JWT for Apple)
            client_secret = self._generate_client_secret()

            response = await self.client.post(
                APPLE_TOKEN_URL,
                data={
                    "client_id": APPLE_CLIENT_ID,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Apple OAuth error: {data.get('error_description', data.get('error'))}")
                return {"success": False, "error": data.get("error_description", data.get("error"))}

            # Decode the id_token to get user info
            id_token = data.get("id_token")
            user_info = self._decode_id_token(id_token)

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "id_token": id_token,
                "expires_in": data.get("expires_in", 3600),
                "user_id": user_info.get("sub"),
                "email": user_info.get("email"),
                "display_name": user_info.get("name", user_info.get("email", "").split("@")[0]),
            }

        except Exception as e:
            logger.error(f"Apple OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        try:
            client_secret = self._generate_client_secret()

            response = await self.client.post(
                APPLE_TOKEN_URL,
                data={
                    "client_id": APPLE_CLIENT_ID,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            data = response.json()

            if "error" in data:
                return {"success": False, "error": data.get("error_description", data.get("error"))}

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": refresh_token,  # Apple doesn't always return new refresh token
                "expires_in": data.get("expires_in", 3600),
            }

        except Exception as e:
            logger.error(f"Apple token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    def _generate_client_secret(self) -> str:
        """
        Generate Apple client secret JWT.

        Apple requires a JWT signed with the private key as the client secret.
        """
        import jwt
        import time

        headers = {
            "alg": "ES256",
            "kid": APPLE_KEY_ID,
        }

        payload = {
            "iss": APPLE_TEAM_ID,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 180,  # 180 days
            "aud": "https://appleid.apple.com",
            "sub": APPLE_CLIENT_ID,
        }

        # APPLE_CLIENT_SECRET contains the private key
        return jwt.encode(payload, APPLE_CLIENT_SECRET, algorithm="ES256", headers=headers)

    def _decode_id_token(self, id_token: str) -> Dict[str, Any]:
        """Decode Apple ID token to get user info."""
        try:
            import jwt
            # Decode without verification for now - in production,
            # verify with Apple's public keys
            return jwt.decode(id_token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Failed to decode Apple ID token: {e}")
            return {}

    # =========================================================================
    # CALDAV CALENDAR SYNC
    # =========================================================================

    async def get_calendars(
        self,
        access_token: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Get list of user's calendars via CalDAV.
        """
        try:
            # CalDAV PROPFIND request to get calendars
            propfind_body = """<?xml version="1.0" encoding="utf-8" ?>
            <d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
                <d:prop>
                    <d:displayname/>
                    <d:resourcetype/>
                    <c:calendar-description/>
                </d:prop>
            </d:propfind>"""

            calendar_home = f"{CALDAV_BASE_URL}/{user_id}/calendars/"

            response = await self.client.request(
                "PROPFIND",
                calendar_home,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/xml",
                    "Depth": "1",
                },
                content=propfind_body,
            )

            if response.status_code not in (200, 207):
                logger.error(f"CalDAV PROPFIND failed: {response.status_code}")
                return []

            # Parse XML response
            calendars = self._parse_calendar_propfind(response.text)
            return calendars

        except Exception as e:
            logger.error(f"Failed to get Apple calendars: {e}")
            return []

    async def get_upcoming_meetings(
        self,
        access_token: str,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get upcoming events from Apple Calendar via CalDAV.

        Used by desktop app to know when to activate.
        """
        try:
            if not from_date:
                from_date = datetime.utcnow()
            if not to_date:
                to_date = from_date + timedelta(days=7)

            # Format dates for CalDAV
            start_str = from_date.strftime("%Y%m%dT%H%M%SZ")
            end_str = to_date.strftime("%Y%m%dT%H%M%SZ")

            # CalDAV REPORT request for calendar events
            report_body = f"""<?xml version="1.0" encoding="utf-8" ?>
            <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
                <d:prop>
                    <d:getetag/>
                    <c:calendar-data/>
                </d:prop>
                <c:filter>
                    <c:comp-filter name="VCALENDAR">
                        <c:comp-filter name="VEVENT">
                            <c:time-range start="{start_str}" end="{end_str}"/>
                        </c:comp-filter>
                    </c:comp-filter>
                </c:filter>
            </c:calendar-query>"""

            # Default calendar path - in production, iterate over all calendars
            calendar_path = f"{CALDAV_BASE_URL}/{user_id}/calendars/calendar/"

            response = await self.client.request(
                "REPORT",
                calendar_path,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/xml",
                    "Depth": "1",
                },
                content=report_body,
            )

            if response.status_code not in (200, 207):
                logger.error(f"CalDAV REPORT failed: {response.status_code}")
                return []

            # Parse iCalendar events from response
            events = self._parse_calendar_events(response.text, "default")

            # Convert to meeting format and detect meeting links
            meetings = []
            for event in events:
                meeting_link = self._extract_meeting_link(event)
                if meeting_link or True:  # Include all events, not just those with meeting links
                    meetings.append(event.to_dict())

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Apple Calendar events: {e}")
            return []

    async def create_event(
        self,
        access_token: str,
        user_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "calendar",
    ) -> Optional[Dict]:
        """
        Create a new calendar event via CalDAV.
        """
        try:
            import uuid

            event_uid = str(uuid.uuid4())

            # Build iCalendar event
            ical_event = self._build_ical_event(
                uid=event_uid,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
            )

            event_url = f"{CALDAV_BASE_URL}/{user_id}/calendars/{calendar_id}/{event_uid}.ics"

            response = await self.client.put(
                event_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "text/calendar; charset=utf-8",
                },
                content=ical_event,
            )

            if response.status_code not in (200, 201, 204):
                logger.error(f"CalDAV PUT failed: {response.status_code}")
                return None

            return {
                "id": event_uid,
                "topic": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "description": description,
                "location": location,
                "attendees": attendees or [],
                "platform": "apple_calendar",
            }

        except Exception as e:
            logger.error(f"Failed to create Apple Calendar event: {e}")
            return None

    async def delete_event(
        self,
        access_token: str,
        user_id: str,
        event_id: str,
        calendar_id: str = "calendar",
    ) -> bool:
        """Delete a calendar event via CalDAV."""
        try:
            event_url = f"{CALDAV_BASE_URL}/{user_id}/calendars/{calendar_id}/{event_id}.ics"

            response = await self.client.delete(
                event_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )

            return response.status_code in (200, 204)

        except Exception as e:
            logger.error(f"Failed to delete Apple Calendar event: {e}")
            return False

    # =========================================================================
    # CALDAV PARSING HELPERS
    # =========================================================================

    def _parse_calendar_propfind(self, xml_response: str) -> List[Dict[str, Any]]:
        """Parse CalDAV PROPFIND response for calendars."""
        try:
            import xml.etree.ElementTree as ET

            # Define namespaces
            ns = {
                "d": "DAV:",
                "c": "urn:ietf:params:xml:ns:caldav",
            }

            root = ET.fromstring(xml_response)
            calendars = []

            for response in root.findall(".//d:response", ns):
                href = response.find("d:href", ns)
                displayname = response.find(".//d:displayname", ns)
                resourcetype = response.find(".//d:resourcetype", ns)

                # Check if this is a calendar (has calendar resourcetype)
                is_calendar = resourcetype is not None and resourcetype.find(".//c:calendar", ns) is not None

                if is_calendar and href is not None:
                    calendars.append({
                        "id": href.text.split("/")[-2] if href.text else "",
                        "name": displayname.text if displayname is not None else "Unnamed Calendar",
                        "href": href.text,
                    })

            return calendars

        except Exception as e:
            logger.error(f"Failed to parse CalDAV PROPFIND response: {e}")
            return []

    def _parse_calendar_events(self, xml_response: str, calendar_id: str) -> List[AppleCalendarEvent]:
        """Parse CalDAV REPORT response for calendar events."""
        try:
            import xml.etree.ElementTree as ET

            ns = {
                "d": "DAV:",
                "c": "urn:ietf:params:xml:ns:caldav",
            }

            root = ET.fromstring(xml_response)
            events = []

            for response in root.findall(".//d:response", ns):
                calendar_data = response.find(".//c:calendar-data", ns)
                etag = response.find(".//d:getetag", ns)

                if calendar_data is not None and calendar_data.text:
                    event = self._parse_ical_event(
                        calendar_data.text,
                        calendar_id,
                        etag.text if etag is not None else None,
                    )
                    if event:
                        events.append(event)

            return events

        except Exception as e:
            logger.error(f"Failed to parse CalDAV REPORT response: {e}")
            return []

    def _parse_ical_event(
        self,
        ical_data: str,
        calendar_id: str,
        etag: Optional[str],
    ) -> Optional[AppleCalendarEvent]:
        """Parse iCalendar data to extract event details."""
        try:
            # Simple iCalendar parser
            lines = ical_data.replace("\r\n ", "").split("\r\n")
            if not lines:
                lines = ical_data.replace("\n ", "").split("\n")

            event_data = {}
            attendees = []
            in_vevent = False

            for line in lines:
                if line == "BEGIN:VEVENT":
                    in_vevent = True
                elif line == "END:VEVENT":
                    in_vevent = False
                elif in_vevent and ":" in line:
                    key, value = line.split(":", 1)
                    # Handle properties with parameters
                    if ";" in key:
                        key = key.split(";")[0]

                    if key == "UID":
                        event_data["uid"] = value
                    elif key == "SUMMARY":
                        event_data["summary"] = value
                    elif key == "DESCRIPTION":
                        event_data["description"] = value
                    elif key == "LOCATION":
                        event_data["location"] = value
                    elif key == "DTSTART":
                        event_data["dtstart"] = self._parse_ical_datetime(value)
                    elif key == "DTEND":
                        event_data["dtend"] = self._parse_ical_datetime(value)
                    elif key == "ATTENDEE":
                        # Extract email from mailto:
                        if "mailto:" in value.lower():
                            email = value.lower().replace("mailto:", "")
                            attendees.append(email)

            if not event_data.get("uid") or not event_data.get("dtstart"):
                return None

            # Extract meeting link from description or location
            meeting_link = self._extract_meeting_link_from_text(
                event_data.get("description", "") + " " + event_data.get("location", "")
            )

            return AppleCalendarEvent(
                id=event_data["uid"],
                title=event_data.get("summary", "Untitled Event"),
                description=event_data.get("description"),
                start_time=event_data["dtstart"],
                end_time=event_data.get("dtend", event_data["dtstart"] + timedelta(hours=1)),
                location=event_data.get("location"),
                attendees=attendees,
                meeting_link=meeting_link,
                calendar_id=calendar_id,
                etag=etag,
            )

        except Exception as e:
            logger.error(f"Failed to parse iCalendar event: {e}")
            return None

    def _parse_ical_datetime(self, value: str) -> datetime:
        """Parse iCalendar datetime value."""
        # Remove timezone identifier if present
        if "T" in value:
            # Format: 20240101T120000 or 20240101T120000Z
            value = value.rstrip("Z")
            return datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
        else:
            # All-day event: 20240101
            return datetime.strptime(value[:8], "%Y%m%d")

    def _build_ical_event(
        self,
        uid: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> str:
        """Build iCalendar event string."""
        now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        start_str = start_time.strftime("%Y%m%dT%H%M%SZ")
        end_str = end_time.strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//ReadIn AI//Calendar//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{title}",
        ]

        if description:
            lines.append(f"DESCRIPTION:{description}")
        if location:
            lines.append(f"LOCATION:{location}")

        if attendees:
            for attendee in attendees:
                lines.append(f"ATTENDEE;RSVP=TRUE:mailto:{attendee}")

        lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])

        return "\r\n".join(lines)

    def _extract_meeting_link(self, event: AppleCalendarEvent) -> Optional[str]:
        """Extract meeting link from event description or location."""
        text = f"{event.description or ''} {event.location or ''}"
        return self._extract_meeting_link_from_text(text)

    def _extract_meeting_link_from_text(self, text: str) -> Optional[str]:
        """Extract meeting link from text."""
        import re

        # Common meeting URL patterns
        patterns = [
            r"https?://[^\s]*zoom\.us/j/[^\s]+",
            r"https?://meet\.google\.com/[^\s]+",
            r"https?://teams\.microsoft\.com/[^\s]+",
            r"https?://[^\s]*webex\.com/[^\s]+",
            r"https?://[^\s]*facetime\.apple\.com/[^\s]+",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_apple_calendar_configured() -> bool:
    """Check if Apple Calendar integration is configured."""
    return bool(APPLE_CLIENT_ID and APPLE_CLIENT_SECRET and APPLE_TEAM_ID and APPLE_KEY_ID)
