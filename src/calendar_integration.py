"""
Calendar Integration for ReadIn AI Desktop App.

STEALTH MODE MEETING DETECTION:
- Syncs with backend calendar APIs (Zoom, Meet, Teams, Webex)
- Detects upcoming and active meetings
- Auto-activates audio capture when meeting starts
- No bots join meetings - completely invisible

This module connects the desktop app to the backend video platform
integrations for automatic meeting detection.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json

import httpx

from config import API_BASE_URL


class MeetingPlatform(Enum):
    """Supported meeting platforms."""
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"
    WEBEX = "webex"
    UNKNOWN = "unknown"


@dataclass
class Meeting:
    """Represents a scheduled meeting."""
    id: str
    topic: str
    platform: MeetingPlatform
    start_time: Optional[datetime]
    duration_minutes: int
    join_url: Optional[str]
    organizer: Optional[str] = None
    attendees: List[str] = None

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

    @property
    def end_time(self) -> Optional[datetime]:
        """Calculate meeting end time."""
        if self.start_time:
            return self.start_time + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def is_active(self) -> bool:
        """Check if meeting is currently in progress."""
        if not self.start_time:
            return False
        now = datetime.utcnow()
        end = self.end_time
        return self.start_time <= now <= end if end else self.start_time <= now

    @property
    def is_upcoming(self) -> bool:
        """Check if meeting is starting soon (within 5 minutes)."""
        if not self.start_time:
            return False
        now = datetime.utcnow()
        return now < self.start_time <= now + timedelta(minutes=5)

    @property
    def minutes_until_start(self) -> Optional[int]:
        """Get minutes until meeting starts."""
        if not self.start_time:
            return None
        delta = self.start_time - datetime.utcnow()
        return max(0, int(delta.total_seconds() / 60))


class CalendarIntegration:
    """
    Integrates with ReadIn AI backend for meeting detection.

    STEALTH MODE:
    - Polls calendar APIs for meeting schedules
    - Detects when meetings start/end
    - Triggers callbacks for auto-activation
    - No visible AI presence in meetings
    """

    def __init__(
        self,
        auth_token: str,
        on_meeting_starting: Optional[Callable[[Meeting], None]] = None,
        on_meeting_ended: Optional[Callable[[Meeting], None]] = None,
        on_meetings_updated: Optional[Callable[[List[Meeting]], None]] = None,
        poll_interval: int = 60,  # seconds
    ):
        self.auth_token = auth_token
        self.on_meeting_starting = on_meeting_starting
        self.on_meeting_ended = on_meeting_ended
        self.on_meetings_updated = on_meetings_updated
        self.poll_interval = poll_interval

        self._client = httpx.Client(
            base_url=API_BASE_URL,
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=30.0,
        )

        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._meetings: List[Meeting] = []
        self._active_meeting: Optional[Meeting] = None
        self._last_poll: Optional[datetime] = None
        self._connected_platforms: List[str] = []

    def get_connected_platforms(self) -> List[Dict[str, Any]]:
        """Get list of connected video platforms."""
        try:
            response = self._client.get("/api/v1/integrations/video-platforms/status")
            if response.status_code == 200:
                data = response.json()
                platforms = data.get("video_platforms", [])
                self._connected_platforms = [
                    p["provider"] for p in platforms if p.get("is_connected")
                ]
                return platforms
            else:
                print(f"Failed to get platforms: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting platforms: {e}")
            return []

    def get_upcoming_meetings(self) -> List[Meeting]:
        """Fetch upcoming meetings from all connected platforms."""
        try:
            response = self._client.get("/api/v1/integrations/meetings/upcoming")
            if response.status_code == 200:
                data = response.json()
                meetings = []
                for m in data.get("meetings", []):
                    try:
                        start_time = None
                        if m.get("start_time"):
                            # Handle various datetime formats
                            start_str = m["start_time"]
                            if "Z" in start_str:
                                start_str = start_str.replace("Z", "+00:00")
                            start_time = datetime.fromisoformat(start_str)

                        platform = MeetingPlatform.UNKNOWN
                        platform_str = m.get("platform", "").lower()
                        if "zoom" in platform_str:
                            platform = MeetingPlatform.ZOOM
                        elif "google" in platform_str or "meet" in platform_str:
                            platform = MeetingPlatform.GOOGLE_MEET
                        elif "teams" in platform_str or "microsoft" in platform_str:
                            platform = MeetingPlatform.MICROSOFT_TEAMS
                        elif "webex" in platform_str:
                            platform = MeetingPlatform.WEBEX

                        meetings.append(Meeting(
                            id=str(m.get("id", "")),
                            topic=m.get("topic", "Meeting"),
                            platform=platform,
                            start_time=start_time,
                            duration_minutes=m.get("duration", 60),
                            join_url=m.get("join_url"),
                            organizer=m.get("organizer"),
                            attendees=m.get("attendees", []),
                        ))
                    except Exception as e:
                        print(f"Error parsing meeting: {e}")
                        continue

                self._meetings = meetings
                self._last_poll = datetime.utcnow()
                return meetings
            else:
                print(f"Failed to get meetings: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching meetings: {e}")
            return []

    def check_active_meeting(self) -> Optional[Meeting]:
        """Check if user is currently in a meeting."""
        try:
            response = self._client.get("/api/v1/integrations/meetings/active")
            if response.status_code == 200:
                data = response.json()
                if data.get("is_in_meeting") and data.get("active_meeting"):
                    m = data["active_meeting"]
                    return Meeting(
                        id=str(m.get("id", "")),
                        topic=m.get("topic", "Active Meeting"),
                        platform=MeetingPlatform.UNKNOWN,
                        start_time=datetime.utcnow(),
                        duration_minutes=60,
                        join_url=m.get("join_url"),
                    )
            return None
        except Exception as e:
            print(f"Error checking active meeting: {e}")
            return None

    def _poll_loop(self):
        """Background polling loop for meeting detection."""
        while self._running:
            try:
                # Fetch upcoming meetings
                meetings = self.get_upcoming_meetings()

                if self.on_meetings_updated:
                    self.on_meetings_updated(meetings)

                # Check for meetings starting now
                for meeting in meetings:
                    if meeting.is_active and self._active_meeting != meeting:
                        # New meeting started
                        self._active_meeting = meeting
                        if self.on_meeting_starting:
                            self.on_meeting_starting(meeting)
                    elif meeting.is_upcoming:
                        # Meeting starting soon - could trigger notification
                        pass

                # Check if active meeting ended
                if self._active_meeting:
                    if not self._active_meeting.is_active:
                        ended_meeting = self._active_meeting
                        self._active_meeting = None
                        if self.on_meeting_ended:
                            self.on_meeting_ended(ended_meeting)

            except Exception as e:
                print(f"Poll error: {e}")

            # Wait for next poll
            for _ in range(self.poll_interval):
                if not self._running:
                    break
                time.sleep(1)

    def start_polling(self):
        """Start background polling for meetings."""
        if self._running:
            return

        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        print("Calendar polling started")

    def stop_polling(self):
        """Stop background polling."""
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None
        print("Calendar polling stopped")

    def get_next_meeting(self) -> Optional[Meeting]:
        """Get the next upcoming meeting."""
        now = datetime.utcnow()
        upcoming = [m for m in self._meetings if m.start_time and m.start_time > now]
        if upcoming:
            return min(upcoming, key=lambda m: m.start_time)
        return None

    def get_current_meeting(self) -> Optional[Meeting]:
        """Get currently active meeting."""
        return self._active_meeting

    @property
    def is_polling(self) -> bool:
        """Check if polling is active."""
        return self._running

    @property
    def meetings(self) -> List[Meeting]:
        """Get cached list of meetings."""
        return self._meetings

    def close(self):
        """Clean up resources."""
        self.stop_polling()
        self._client.close()


class MeetingAutoActivator:
    """
    Automatically activates ReadIn AI when meetings start.

    STEALTH MODE WORKFLOW:
    1. User connects video platforms in web dashboard
    2. Desktop app polls calendar for meetings
    3. When meeting starts, auto-activate audio capture
    4. AI assistance is completely invisible to others
    """

    def __init__(
        self,
        calendar: CalendarIntegration,
        on_activate: Callable[[Meeting], None],
        on_deactivate: Callable[[Meeting], None],
        pre_meeting_buffer: int = 1,  # Start capturing 1 minute before
    ):
        self.calendar = calendar
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self.pre_meeting_buffer = pre_meeting_buffer

        self._active = False
        self._current_meeting: Optional[Meeting] = None

        # Register callbacks
        self.calendar.on_meeting_starting = self._handle_meeting_start
        self.calendar.on_meeting_ended = self._handle_meeting_end

    def _handle_meeting_start(self, meeting: Meeting):
        """Handle meeting start event."""
        if not self._active:
            print(f"Meeting starting: {meeting.topic} ({meeting.platform.value})")
            self._active = True
            self._current_meeting = meeting
            self.on_activate(meeting)

    def _handle_meeting_end(self, meeting: Meeting):
        """Handle meeting end event."""
        if self._active:
            print(f"Meeting ended: {meeting.topic}")
            self._active = False
            self.on_deactivate(meeting)
            self._current_meeting = None

    @property
    def is_active(self) -> bool:
        """Check if auto-activation is currently triggered."""
        return self._active

    @property
    def current_meeting(self) -> Optional[Meeting]:
        """Get the meeting that triggered activation."""
        return self._current_meeting


def create_meeting_detector(
    auth_token: str,
    on_meeting_start: Callable[[Meeting], None],
    on_meeting_end: Callable[[Meeting], None],
) -> CalendarIntegration:
    """
    Factory function to create a meeting detector.

    Usage:
        detector = create_meeting_detector(
            auth_token="user_jwt_token",
            on_meeting_start=lambda m: print(f"Started: {m.topic}"),
            on_meeting_end=lambda m: print(f"Ended: {m.topic}"),
        )
        detector.start_polling()
    """
    calendar = CalendarIntegration(
        auth_token=auth_token,
        on_meeting_starting=on_meeting_start,
        on_meeting_ended=on_meeting_end,
        poll_interval=30,  # Check every 30 seconds
    )
    return calendar


if __name__ == "__main__":
    # Test the calendar integration
    import os

    token = os.getenv("READIN_AUTH_TOKEN", "")
    if not token:
        print("Set READIN_AUTH_TOKEN environment variable to test")
        exit(1)

    def on_start(meeting):
        print(f"\n>>> MEETING STARTED: {meeting.topic}")
        print(f"    Platform: {meeting.platform.value}")
        print(f"    Join URL: {meeting.join_url}")

    def on_end(meeting):
        print(f"\n<<< MEETING ENDED: {meeting.topic}")

    detector = create_meeting_detector(token, on_start, on_end)

    # Check connected platforms
    print("Connected platforms:")
    platforms = detector.get_connected_platforms()
    for p in platforms:
        status = "Connected" if p.get("is_connected") else "Not connected"
        print(f"  {p['display_name']}: {status}")

    # Get upcoming meetings
    print("\nUpcoming meetings:")
    meetings = detector.get_upcoming_meetings()
    for m in meetings:
        print(f"  - {m.topic} ({m.platform.value})")
        if m.start_time:
            print(f"    Starts: {m.start_time}")
            if m.minutes_until_start is not None:
                print(f"    In: {m.minutes_until_start} minutes")

    # Start polling
    print("\nStarting meeting detection (Ctrl+C to stop)...")
    detector.start_polling()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        detector.close()
