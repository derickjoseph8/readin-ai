"""
Calendar Integration Service

Provides functionality to read calendar events from:
- Google Calendar
- Microsoft Outlook
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")


@dataclass
class CalendarEvent:
    """Unified calendar event structure."""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    meeting_link: Optional[str]
    calendar_provider: str  # google, microsoft
    raw_data: dict


class CalendarService:
    """Service for reading calendar events from various providers."""

    @staticmethod
    async def refresh_google_token(refresh_token: str) -> Optional[str]:
        """Refresh Google access token using refresh token."""
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            return None

    @staticmethod
    async def refresh_microsoft_token(refresh_token: str) -> Optional[str]:
        """Refresh Microsoft access token using refresh token."""
        if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                data={
                    "client_id": MICROSOFT_CLIENT_ID,
                    "client_secret": MICROSOFT_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            return None

    @staticmethod
    async def get_google_events(
        access_token: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 50
    ) -> List[CalendarEvent]:
        """
        Fetch calendar events from Google Calendar.

        Args:
            access_token: Valid Google OAuth access token
            start_date: Start of date range (defaults to today)
            end_date: End of date range (defaults to 7 days from now)
            max_results: Maximum number of events to return

        Returns:
            List of CalendarEvent objects
        """
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        params = {
            "timeMin": start_date.isoformat() + "Z",
            "timeMax": end_date.isoformat() + "Z",
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime"
        }

        events = []
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params
            )

            if response.status_code != 200:
                return events

            data = response.json()
            for item in data.get("items", []):
                # Parse start/end times
                start = item.get("start", {})
                end = item.get("end", {})

                start_time = start.get("dateTime") or start.get("date")
                end_time = end.get("dateTime") or end.get("date")

                # Parse datetime
                if "T" in (start_time or ""):
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                else:
                    start_dt = datetime.fromisoformat(start_time) if start_time else datetime.utcnow()

                if "T" in (end_time or ""):
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                else:
                    end_dt = datetime.fromisoformat(end_time) if end_time else start_dt + timedelta(hours=1)

                # Extract attendees
                attendees = [
                    a.get("email", "")
                    for a in item.get("attendees", [])
                    if a.get("email")
                ]

                # Extract meeting link
                meeting_link = None
                if item.get("hangoutLink"):
                    meeting_link = item["hangoutLink"]
                elif item.get("conferenceData", {}).get("entryPoints"):
                    for ep in item["conferenceData"]["entryPoints"]:
                        if ep.get("entryPointType") == "video":
                            meeting_link = ep.get("uri")
                            break

                events.append(CalendarEvent(
                    id=item.get("id", ""),
                    title=item.get("summary", "Untitled"),
                    description=item.get("description"),
                    start_time=start_dt,
                    end_time=end_dt,
                    location=item.get("location"),
                    attendees=attendees,
                    meeting_link=meeting_link,
                    calendar_provider="google",
                    raw_data=item
                ))

        return events

    @staticmethod
    async def get_microsoft_events(
        access_token: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_results: int = 50
    ) -> List[CalendarEvent]:
        """
        Fetch calendar events from Microsoft Outlook.

        Args:
            access_token: Valid Microsoft OAuth access token
            start_date: Start of date range (defaults to today)
            end_date: End of date range (defaults to 7 days from now)
            max_results: Maximum number of events to return

        Returns:
            List of CalendarEvent objects
        """
        if not start_date:
            start_date = datetime.utcnow()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        events = []
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/calendarView",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "startDateTime": start_date.isoformat() + "Z",
                    "endDateTime": end_date.isoformat() + "Z",
                    "$top": max_results,
                    "$orderby": "start/dateTime",
                    "$select": "id,subject,body,start,end,location,attendees,onlineMeeting,onlineMeetingUrl"
                }
            )

            if response.status_code != 200:
                return events

            data = response.json()
            for item in data.get("value", []):
                # Parse start/end times
                start_str = item.get("start", {}).get("dateTime", "")
                end_str = item.get("end", {}).get("dateTime", "")

                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")) if start_str else datetime.utcnow()
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else start_dt + timedelta(hours=1)

                # Extract attendees
                attendees = [
                    a.get("emailAddress", {}).get("address", "")
                    for a in item.get("attendees", [])
                    if a.get("emailAddress", {}).get("address")
                ]

                # Extract meeting link
                meeting_link = item.get("onlineMeetingUrl")
                if not meeting_link and item.get("onlineMeeting"):
                    meeting_link = item["onlineMeeting"].get("joinUrl")

                # Extract location
                location = None
                loc_data = item.get("location")
                if loc_data:
                    location = loc_data.get("displayName")

                events.append(CalendarEvent(
                    id=item.get("id", ""),
                    title=item.get("subject", "Untitled"),
                    description=item.get("body", {}).get("content"),
                    start_time=start_dt,
                    end_time=end_dt,
                    location=location,
                    attendees=attendees,
                    meeting_link=meeting_link,
                    calendar_provider="microsoft",
                    raw_data=item
                ))

        return events

    @staticmethod
    async def get_upcoming_meetings(
        user,
        hours_ahead: int = 24
    ) -> List[CalendarEvent]:
        """
        Get upcoming meetings from all connected calendars.

        Args:
            user: User object with calendar tokens
            hours_ahead: How many hours ahead to look

        Returns:
            List of CalendarEvent objects sorted by start time
        """
        events = []
        now = datetime.utcnow()
        end = now + timedelta(hours=hours_ahead)

        # Get Google events
        if user.google_refresh_token:
            access_token = await CalendarService.refresh_google_token(user.google_refresh_token)
            if access_token:
                google_events = await CalendarService.get_google_events(
                    access_token, now, end
                )
                events.extend(google_events)

        # Get Microsoft events
        if user.microsoft_refresh_token:
            access_token = await CalendarService.refresh_microsoft_token(user.microsoft_refresh_token)
            if access_token:
                ms_events = await CalendarService.get_microsoft_events(
                    access_token, now, end
                )
                events.extend(ms_events)

        # Sort by start time
        events.sort(key=lambda e: e.start_time)
        return events
