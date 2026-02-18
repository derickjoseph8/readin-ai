"""
Calendly Integration Service for ReadIn AI.

PRIVACY-FIRST DESIGN:
- NO bot joins meetings (completely invisible to other participants)
- Local audio capture only via desktop app
- Calendly event sync for meeting detection
- Webhook support for real-time booking notifications
- Per-user OAuth tokens (data isolation)

Provides:
- OAuth 2.0 authentication with Calendly
- Fetch scheduled events
- Webhook handling for new bookings
- Link Calendly events to ReadIn meetings
- Event type management
"""

import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from config import (
    CALENDLY_CLIENT_ID,
    CALENDLY_CLIENT_SECRET,
    CALENDLY_WEBHOOK_SECRET,
    APP_URL,
)

logger = logging.getLogger("calendly")

# Calendly API endpoints
CALENDLY_API_BASE = "https://api.calendly.com"
CALENDLY_AUTH_URL = "https://auth.calendly.com/oauth/authorize"
CALENDLY_TOKEN_URL = "https://auth.calendly.com/oauth/token"


@dataclass
class CalendlyEvent:
    """Represents a Calendly scheduled event."""
    uri: str
    name: str
    status: str  # active, canceled
    start_time: datetime
    end_time: datetime
    location: Optional[Dict[str, Any]]
    invitees_counter: Dict[str, int]
    event_type: str
    meeting_link: Optional[str]
    created_at: datetime
    updated_at: datetime
    cancellation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        # Extract the event UUID from URI
        event_id = self.uri.split("/")[-1] if self.uri else ""

        # Determine join URL based on location type
        join_url = None
        if self.location:
            join_url = self.location.get("join_url") or self.meeting_link

        return {
            "id": event_id,
            "uri": self.uri,
            "topic": self.name,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": int((self.end_time - self.start_time).total_seconds() / 60) if self.start_time and self.end_time else 30,
            "location": self.location,
            "join_url": join_url,
            "invitees_count": self.invitees_counter.get("total", 0),
            "event_type": self.event_type,
            "platform": "calendly",
        }


class CalendlyService:
    """
    Calendly integration service for ReadIn AI.

    IMPORTANT: This integration does NOT join meetings as a bot.
    It syncs Calendly events to detect meeting schedules.
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
        Generate Calendly OAuth authorization URL.

        Scopes requested are minimal - only what's needed for event sync.
        """
        state = f"{user_id}:calendly:{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": CALENDLY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{CALENDLY_AUTH_URL}?{query}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            response = await self.client.post(
                CALENDLY_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": CALENDLY_CLIENT_ID,
                    "client_secret": CALENDLY_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Calendly OAuth error: {data.get('error_description', data.get('error'))}")
                return {"success": False, "error": data.get("error_description", data.get("error"))}

            # Get user info
            user_info = await self._get_user_info(data.get("access_token"))

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 7200),
                "token_type": data.get("token_type", "Bearer"),
                "user_uri": user_info.get("uri"),
                "user_id": user_info.get("uri", "").split("/")[-1] if user_info.get("uri") else None,
                "email": user_info.get("email"),
                "display_name": user_info.get("name"),
                "organization_uri": user_info.get("current_organization"),
            }

        except Exception as e:
            logger.error(f"Calendly OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token."""
        try:
            response = await self.client.post(
                CALENDLY_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": CALENDLY_CLIENT_ID,
                    "client_secret": CALENDLY_CLIENT_SECRET,
                    "refresh_token": refresh_token,
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
                "refresh_token": data.get("refresh_token", refresh_token),
                "expires_in": data.get("expires_in", 7200),
            }

        except Exception as e:
            logger.error(f"Calendly token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get current user info from Calendly."""
        try:
            response = await self.client.get(
                f"{CALENDLY_API_BASE}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()
            return data.get("resource", {})

        except Exception as e:
            logger.error(f"Failed to get Calendly user info: {e}")
            return {}

    # =========================================================================
    # EVENT SYNC
    # =========================================================================

    async def get_upcoming_meetings(
        self,
        access_token: str,
        user_uri: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get upcoming Calendly events.

        Used by desktop app to know when to activate for meetings.
        """
        try:
            # Get user URI if not provided
            if not user_uri:
                user_info = await self._get_user_info(access_token)
                user_uri = user_info.get("uri")
                if not user_uri:
                    logger.error("Could not determine Calendly user URI")
                    return []

            if not from_date:
                from_date = datetime.utcnow()
            if not to_date:
                to_date = from_date + timedelta(days=14)

            params = {
                "user": user_uri,
                "min_start_time": from_date.isoformat() + "Z",
                "max_start_time": to_date.isoformat() + "Z",
                "status": "active",
                "count": 50,
            }

            response = await self.client.get(
                f"{CALENDLY_API_BASE}/scheduled_events",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "error" in data or response.status_code != 200:
                logger.error(f"Calendly API error: {data}")
                return []

            meetings = []
            for event in data.get("collection", []):
                calendly_event = self._parse_event(event)
                if calendly_event:
                    meetings.append(calendly_event.to_dict())

            return meetings

        except Exception as e:
            logger.error(f"Failed to get Calendly events: {e}")
            return []

    async def get_event_details(
        self,
        access_token: str,
        event_uri: str,
    ) -> Optional[Dict]:
        """Get details for a specific Calendly event."""
        try:
            # Extract UUID from URI if full URI provided
            event_uuid = event_uri.split("/")[-1] if "/" in event_uri else event_uri

            response = await self.client.get(
                f"{CALENDLY_API_BASE}/scheduled_events/{event_uuid}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()

            if "error" in data or response.status_code != 200:
                return None

            event = self._parse_event(data.get("resource", {}))
            if event:
                return event.to_dict()

            return None

        except Exception as e:
            logger.error(f"Failed to get Calendly event details: {e}")
            return None

    async def get_event_invitees(
        self,
        access_token: str,
        event_uri: str,
    ) -> List[Dict]:
        """Get list of invitees for a Calendly event."""
        try:
            event_uuid = event_uri.split("/")[-1] if "/" in event_uri else event_uri

            response = await self.client.get(
                f"{CALENDLY_API_BASE}/scheduled_events/{event_uuid}/invitees",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()

            if "error" in data or response.status_code != 200:
                return []

            invitees = []
            for invitee in data.get("collection", []):
                invitees.append({
                    "uri": invitee.get("uri"),
                    "email": invitee.get("email"),
                    "name": invitee.get("name"),
                    "status": invitee.get("status"),
                    "timezone": invitee.get("timezone"),
                    "created_at": invitee.get("created_at"),
                })

            return invitees

        except Exception as e:
            logger.error(f"Failed to get Calendly invitees: {e}")
            return []

    def _parse_event(self, event_data: Dict) -> Optional[CalendlyEvent]:
        """Parse Calendly event data into CalendlyEvent object."""
        try:
            start_time = None
            end_time = None

            if event_data.get("start_time"):
                start_time = datetime.fromisoformat(
                    event_data["start_time"].replace("Z", "+00:00")
                )
            if event_data.get("end_time"):
                end_time = datetime.fromisoformat(
                    event_data["end_time"].replace("Z", "+00:00")
                )

            # Extract meeting link from location
            location = event_data.get("location", {})
            meeting_link = None
            if location:
                meeting_link = location.get("join_url")

            return CalendlyEvent(
                uri=event_data.get("uri", ""),
                name=event_data.get("name", "Calendly Meeting"),
                status=event_data.get("status", "active"),
                start_time=start_time,
                end_time=end_time,
                location=location,
                invitees_counter=event_data.get("invitees_counter", {}),
                event_type=event_data.get("event_type", ""),
                meeting_link=meeting_link,
                created_at=datetime.fromisoformat(
                    event_data.get("created_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    event_data.get("updated_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                ),
                cancellation=event_data.get("cancellation"),
            )

        except Exception as e:
            logger.error(f"Failed to parse Calendly event: {e}")
            return None

    # =========================================================================
    # EVENT TYPES
    # =========================================================================

    async def get_event_types(
        self,
        access_token: str,
        user_uri: Optional[str] = None,
    ) -> List[Dict]:
        """Get user's Calendly event types."""
        try:
            if not user_uri:
                user_info = await self._get_user_info(access_token)
                user_uri = user_info.get("uri")

            params = {"user": user_uri} if user_uri else {}

            response = await self.client.get(
                f"{CALENDLY_API_BASE}/event_types",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )

            data = response.json()

            if "error" in data or response.status_code != 200:
                return []

            event_types = []
            for et in data.get("collection", []):
                event_types.append({
                    "uri": et.get("uri"),
                    "name": et.get("name"),
                    "slug": et.get("slug"),
                    "duration": et.get("duration"),
                    "scheduling_url": et.get("scheduling_url"),
                    "active": et.get("active", True),
                    "color": et.get("color"),
                    "description": et.get("description_plain"),
                })

            return event_types

        except Exception as e:
            logger.error(f"Failed to get Calendly event types: {e}")
            return []

    # =========================================================================
    # WEBHOOK MANAGEMENT
    # =========================================================================

    async def create_webhook_subscription(
        self,
        access_token: str,
        organization_uri: str,
        events: List[str] = None,
    ) -> Optional[Dict]:
        """
        Create a webhook subscription for Calendly events.

        Events can include:
        - invitee.created
        - invitee.canceled
        - invitee_no_show.created
        """
        try:
            if events is None:
                events = ["invitee.created", "invitee.canceled"]

            callback_url = f"{APP_URL}/api/integrations/calendly/webhook"

            response = await self.client.post(
                f"{CALENDLY_API_BASE}/webhook_subscriptions",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": callback_url,
                    "events": events,
                    "organization": organization_uri,
                    "scope": "organization",
                },
            )

            data = response.json()

            if response.status_code not in (200, 201):
                logger.error(f"Failed to create Calendly webhook: {data}")
                return None

            resource = data.get("resource", {})
            return {
                "uri": resource.get("uri"),
                "callback_url": resource.get("callback_url"),
                "events": resource.get("events", []),
                "state": resource.get("state"),
                "created_at": resource.get("created_at"),
            }

        except Exception as e:
            logger.error(f"Failed to create Calendly webhook: {e}")
            return None

    async def list_webhook_subscriptions(
        self,
        access_token: str,
        organization_uri: str,
    ) -> List[Dict]:
        """List all webhook subscriptions."""
        try:
            response = await self.client.get(
                f"{CALENDLY_API_BASE}/webhook_subscriptions",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"organization": organization_uri},
            )

            data = response.json()

            if response.status_code != 200:
                return []

            webhooks = []
            for wh in data.get("collection", []):
                webhooks.append({
                    "uri": wh.get("uri"),
                    "callback_url": wh.get("callback_url"),
                    "events": wh.get("events", []),
                    "state": wh.get("state"),
                    "created_at": wh.get("created_at"),
                })

            return webhooks

        except Exception as e:
            logger.error(f"Failed to list Calendly webhooks: {e}")
            return []

    async def delete_webhook_subscription(
        self,
        access_token: str,
        webhook_uri: str,
    ) -> bool:
        """Delete a webhook subscription."""
        try:
            webhook_uuid = webhook_uri.split("/")[-1] if "/" in webhook_uri else webhook_uri

            response = await self.client.delete(
                f"{CALENDLY_API_BASE}/webhook_subscriptions/{webhook_uuid}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            return response.status_code in (200, 204)

        except Exception as e:
            logger.error(f"Failed to delete Calendly webhook: {e}")
            return False

    # =========================================================================
    # WEBHOOK HANDLING
    # =========================================================================

    def verify_webhook_signature(
        self,
        signature: str,
        timestamp: str,
        body: bytes,
    ) -> bool:
        """
        Verify Calendly webhook signature.

        Calendly uses HMAC-SHA256 for webhook signature verification.
        """
        if not CALENDLY_WEBHOOK_SECRET:
            logger.warning("Calendly webhook secret not configured")
            return True  # Skip verification if not configured

        try:
            # Construct the signed payload
            signed_payload = f"{timestamp}.{body.decode('utf-8')}"

            # Calculate expected signature
            expected_signature = hmac.new(
                CALENDLY_WEBHOOK_SECRET.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures (extract just the signature part if prefixed)
            if signature.startswith("v1="):
                signature = signature[3:]

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    async def handle_webhook_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle incoming Calendly webhook event.

        Returns processed event data for ReadIn AI integration.
        """
        try:
            event_data = payload.get("payload", {})

            if event_type == "invitee.created":
                # New booking created
                scheduled_event = event_data.get("scheduled_event", {})
                invitee = event_data.get("invitee", {})

                return {
                    "type": "booking_created",
                    "event_uri": scheduled_event.get("uri"),
                    "event_name": scheduled_event.get("name"),
                    "start_time": scheduled_event.get("start_time"),
                    "end_time": scheduled_event.get("end_time"),
                    "invitee_email": invitee.get("email"),
                    "invitee_name": invitee.get("name"),
                    "location": scheduled_event.get("location"),
                    "questions_and_answers": invitee.get("questions_and_answers", []),
                    "created_at": event_data.get("created_at"),
                }

            elif event_type == "invitee.canceled":
                # Booking canceled
                scheduled_event = event_data.get("scheduled_event", {})
                invitee = event_data.get("invitee", {})
                cancellation = invitee.get("cancellation", {})

                return {
                    "type": "booking_canceled",
                    "event_uri": scheduled_event.get("uri"),
                    "event_name": scheduled_event.get("name"),
                    "invitee_email": invitee.get("email"),
                    "invitee_name": invitee.get("name"),
                    "canceler_type": cancellation.get("canceler_type"),
                    "reason": cancellation.get("reason"),
                    "canceled_at": cancellation.get("canceled_at"),
                }

            elif event_type == "invitee_no_show.created":
                # Invitee marked as no-show
                scheduled_event = event_data.get("scheduled_event", {})
                invitee = event_data.get("invitee", {})

                return {
                    "type": "no_show",
                    "event_uri": scheduled_event.get("uri"),
                    "event_name": scheduled_event.get("name"),
                    "invitee_email": invitee.get("email"),
                    "invitee_name": invitee.get("name"),
                    "created_at": event_data.get("created_at"),
                }

            else:
                logger.warning(f"Unknown Calendly webhook event type: {event_type}")
                return {"type": "unknown", "raw_event_type": event_type}

        except Exception as e:
            logger.error(f"Failed to handle Calendly webhook: {e}")
            return {"type": "error", "error": str(e)}

    # =========================================================================
    # READIN AI MEETING LINKING
    # =========================================================================

    async def link_to_readin_meeting(
        self,
        access_token: str,
        calendly_event_uri: str,
        readin_meeting_id: int,
    ) -> bool:
        """
        Link a Calendly event to a ReadIn AI meeting.

        This allows briefings and summaries to be associated with
        Calendly bookings.
        """
        try:
            # Get event details
            event = await self.get_event_details(access_token, calendly_event_uri)
            if not event:
                return False

            # Get invitees for contact matching
            invitees = await self.get_event_invitees(access_token, calendly_event_uri)

            # Store the link in database (implementation depends on your models)
            # This is a placeholder - implement based on your Meeting model
            logger.info(
                f"Linking Calendly event {calendly_event_uri} to ReadIn meeting {readin_meeting_id}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to link Calendly event to ReadIn meeting: {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_calendly_configured() -> bool:
    """Check if Calendly integration is configured."""
    return bool(CALENDLY_CLIENT_ID and CALENDLY_CLIENT_SECRET)
