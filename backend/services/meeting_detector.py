"""
Unified Meeting Detection Service for ReadIn AI.

PRIVACY-FIRST DESIGN - ALL PLATFORMS:
===========================================
- NO bots join any meetings (Zoom, Meet, Teams, Webex)
- NO visible AI presence to other participants
- Local audio capture ONLY via desktop app
- Calendar sync for meeting schedule detection
- Per-user OAuth tokens (complete data isolation)

This service provides:
- Unified interface for all video platforms
- Meeting schedule aggregation
- Active meeting detection
- Desktop app coordination

SUPPORTED PLATFORMS:
- Zoom
- Google Meet
- Microsoft Teams (video calls)
- Cisco Webex
- Apple Calendar (CalDAV)
- Calendly
- Generic (calendar-based detection)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy.orm import Session

from models import UserIntegration

logger = logging.getLogger("meeting_detector")


class MeetingPlatform(str, Enum):
    """Supported meeting platforms."""
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"
    WEBEX = "webex"
    APPLE_CALENDAR = "apple_calendar"
    CALENDLY = "calendly"
    GENERIC = "generic"  # For calendar-detected meetings without specific platform


class MeetingDetector:
    """
    Unified meeting detection across all platforms.

    PRIVACY GUARANTEE:
    - This service NEVER joins meetings
    - This service NEVER sends bots or agents
    - This service ONLY reads calendar/schedule data
    - Actual meeting capture is done locally by desktop app
    """

    def __init__(self, db: Session):
        self.db = db
        self._services = {}

    async def get_all_upcoming_meetings(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get all upcoming meetings across all connected platforms.

        Returns unified list sorted by start time.
        """
        if not from_date:
            from_date = datetime.utcnow()
        if not to_date:
            to_date = from_date + timedelta(days=7)

        all_meetings = []

        # Get user's connected integrations
        integrations = self.db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.is_active == True,
            UserIntegration.provider.in_([
                "zoom", "google_meet", "microsoft_teams", "webex",
                "apple_calendar", "calendly"
            ])
        ).all()

        for integration in integrations:
            try:
                meetings = await self._get_meetings_for_platform(
                    integration, from_date, to_date
                )
                all_meetings.extend(meetings)
            except Exception as e:
                logger.error(f"Error getting meetings for {integration.provider}: {e}")

        # Sort by start time
        all_meetings.sort(key=lambda m: m.get("start_time") or "")

        return all_meetings

    async def _get_meetings_for_platform(
        self,
        integration: UserIntegration,
        from_date: datetime,
        to_date: datetime,
    ) -> List[Dict]:
        """Get meetings for a specific platform integration."""
        provider = integration.provider

        if provider == "zoom":
            from services.zoom_service import ZoomService
            service = ZoomService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token, from_date, to_date
            )
            await service.close()
            return meetings

        elif provider == "google_meet":
            from services.google_meet_service import GoogleMeetService
            service = GoogleMeetService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token, from_date, to_date
            )
            await service.close()
            return meetings

        elif provider == "microsoft_teams":
            from services.teams_meeting_service import TeamsMeetingService
            service = TeamsMeetingService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token, from_date, to_date
            )
            await service.close()
            return meetings

        elif provider == "webex":
            from services.webex_service import WebexService
            service = WebexService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token, from_date, to_date
            )
            await service.close()
            return meetings

        elif provider == "apple_calendar":
            from services.apple_calendar_service import AppleCalendarService
            service = AppleCalendarService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token,
                integration.provider_user_id,
                from_date, to_date
            )
            await service.close()
            return meetings

        elif provider == "calendly":
            from services.calendly_service import CalendlyService
            service = CalendlyService(self.db)
            meetings = await service.get_upcoming_meetings(
                integration.access_token, None, from_date, to_date
            )
            await service.close()
            return meetings

        return []

    async def check_active_meeting(
        self,
        user_id: int,
    ) -> Optional[Dict]:
        """
        Check if user is currently in any meeting.

        Used by desktop app to detect meeting state.
        """
        integrations = self.db.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.is_active == True,
            UserIntegration.provider.in_([
                "zoom", "google_meet", "microsoft_teams", "webex",
                "apple_calendar", "calendly"
            ])
        ).all()

        for integration in integrations:
            try:
                active = await self._check_active_for_platform(integration)
                if active:
                    return active
            except Exception as e:
                logger.error(f"Error checking active meeting for {integration.provider}: {e}")

        return None

    async def _check_active_for_platform(
        self,
        integration: UserIntegration,
    ) -> Optional[Dict]:
        """Check for active meeting on specific platform."""
        provider = integration.provider

        if provider == "zoom":
            from services.zoom_service import ZoomService
            service = ZoomService(self.db)
            active = await service.check_active_meeting(integration.access_token)
            await service.close()
            return active

        # Other platforms typically require calendar-based detection
        # since they don't have "live meeting" APIs
        return None

    def detect_platform_from_url(self, url: str) -> MeetingPlatform:
        """
        Detect meeting platform from URL.

        Used by desktop app for URL-based detection.
        """
        url_lower = url.lower()

        if "zoom.us" in url_lower:
            return MeetingPlatform.ZOOM
        elif "meet.google.com" in url_lower:
            return MeetingPlatform.GOOGLE_MEET
        elif "teams.microsoft.com" in url_lower or "teams.live.com" in url_lower:
            return MeetingPlatform.MICROSOFT_TEAMS
        elif "webex.com" in url_lower:
            return MeetingPlatform.WEBEX
        elif "calendly.com" in url_lower:
            return MeetingPlatform.CALENDLY
        elif "facetime.apple.com" in url_lower:
            return MeetingPlatform.APPLE_CALENDAR
        else:
            return MeetingPlatform.GENERIC

    async def get_meeting_context(
        self,
        user_id: int,
        meeting_url: str,
    ) -> Optional[Dict]:
        """
        Get context for a meeting based on URL.

        Used to provide briefing info when user joins a meeting.
        """
        platform = self.detect_platform_from_url(meeting_url)

        # Get upcoming meetings and find matching one
        meetings = await self.get_all_upcoming_meetings(user_id)

        for meeting in meetings:
            if meeting.get("join_url") and meeting_url in meeting.get("join_url"):
                return {
                    "meeting": meeting,
                    "platform": platform,
                    "has_context": True,
                }

        # No calendar match - generic meeting
        return {
            "meeting": None,
            "platform": platform,
            "has_context": False,
        }


# =============================================================================
# STEALTH MODE DOCUMENTATION
# =============================================================================

"""
HOW STEALTH MODE WORKS:
=======================

1. User installs ReadIn AI desktop app
2. User connects video platform accounts (Zoom, Meet, etc.)
3. ReadIn syncs calendar to know meeting schedules

When user joins a meeting:
4. Desktop app detects meeting window/audio
5. Desktop app captures SYSTEM AUDIO locally
6. Audio is processed locally or sent to ReadIn API
7. AI provides real-time assistance in overlay

What OTHER participants see:
- NOTHING extra
- NO bot in participant list
- NO "Recording" indicator
- NO AI presence whatsoever

Privacy is ABSOLUTE - other participants cannot detect ReadIn AI.

TECHNICAL IMPLEMENTATION:
- Desktop app uses system audio capture (like OBS/screen recorders)
- No API calls to join meetings as participant
- No webhooks that would indicate AI presence
- Calendar sync is read-only
"""
