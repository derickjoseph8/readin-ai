"""
HubSpot CRM Integration Service for ReadIn AI.

Provides:
- OAuth 2.0 authentication with HubSpot
- Contact management
- Meeting engagement logging
- Notes/activity sync
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from config import (
    HUBSPOT_CLIENT_ID,
    HUBSPOT_CLIENT_SECRET,
    APP_URL,
)

logger = logging.getLogger("hubspot")

# HubSpot API endpoints
HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_API_BASE = "https://api.hubapi.com"


@dataclass
class HubSpotConnection:
    """Represents a connected HubSpot account."""
    access_token: str
    refresh_token: str
    hub_id: str
    user_id: str
    display_name: Optional[str] = None


class HubSpotService:
    """
    HubSpot CRM integration service for ReadIn AI.

    Handles OAuth, contact management, and engagement logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate HubSpot OAuth authorization URL.

        Args:
            user_id: User initiating the connection
            redirect_uri: Callback URL after authorization

        Returns:
            OAuth authorization URL
        """
        scopes = [
            "crm.objects.contacts.read",
            "crm.objects.contacts.write",
            "crm.objects.companies.read",
            "crm.objects.companies.write",
            "crm.objects.deals.read",
            "sales-email-read",
            "timeline",
        ]

        state = f"{user_id}:{int(time.time())}"

        params = {
            "client_id": HUBSPOT_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{HUBSPOT_AUTH_URL}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        try:
            response = await self.client.post(
                HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": HUBSPOT_CLIENT_ID,
                    "client_secret": HUBSPOT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"HubSpot OAuth error: {data.get('message')}")
                return {"success": False, "error": data.get("message")}

            # Get account info
            access_token = data.get("access_token")
            account_info = await self._get_account_info(access_token)

            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 21600),  # 6 hours default
                "hub_id": str(account_info.get("portalId", "")),
                "user_id": str(account_info.get("userId", "")),
                "display_name": account_info.get("user", ""),
                "hub_domain": account_info.get("hub_domain", ""),
            }

        except Exception as e:
            logger.error(f"HubSpot OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token data
        """
        try:
            response = await self.client.post(
                HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": HUBSPOT_CLIENT_ID,
                    "client_secret": HUBSPOT_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"HubSpot token refresh error: {data.get('message')}")
                return {"success": False, "error": data.get("message")}

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 21600),
            }

        except Exception as e:
            logger.error(f"HubSpot token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_account_info(self, access_token: str) -> Dict[str, Any]:
        """Get current account information from HubSpot."""
        try:
            response = await self.client.get(
                f"{HUBSPOT_API_BASE}/account-info/v3/details",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get HubSpot account info: {e}")
            return {}

    # =========================================================================
    # CONTACT MANAGEMENT
    # =========================================================================

    async def find_contact_by_email(
        self,
        access_token: str,
        email: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a Contact in HubSpot by email address.

        Args:
            access_token: Valid access token
            email: Email address to search

        Returns:
            Contact record or None
        """
        try:
            response = await self.client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "email",
                                    "operator": "EQ",
                                    "value": email,
                                }
                            ]
                        }
                    ],
                    "properties": ["firstname", "lastname", "email", "jobtitle", "company"],
                },
            )

            data = response.json()

            if data.get("total", 0) > 0:
                return data["results"][0]
            return None

        except Exception as e:
            logger.error(f"Failed to find HubSpot contact: {e}")
            return None

    async def create_contact(
        self,
        access_token: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new Contact in HubSpot.

        Args:
            access_token: Valid access token
            contact_data: Contact properties

        Returns:
            Created contact info including id
        """
        try:
            response = await self.client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": contact_data},
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "id": data.get("id"),
                }
            else:
                logger.error(f"HubSpot create contact error: {data}")
                return {"success": False, "error": data.get("message", str(data))}

        except Exception as e:
            logger.error(f"Failed to create HubSpot contact: {e}")
            return {"success": False, "error": str(e)}

    async def update_contact(
        self,
        access_token: str,
        contact_id: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing Contact in HubSpot.

        Args:
            access_token: Valid access token
            contact_id: HubSpot Contact ID
            contact_data: Properties to update

        Returns:
            Success status
        """
        try:
            response = await self.client.patch(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": contact_data},
            )

            if response.status_code == 200:
                return {"success": True, "id": contact_id}
            else:
                data = response.json()
                logger.error(f"HubSpot update contact error: {data}")
                return {"success": False, "error": data.get("message", str(data))}

        except Exception as e:
            logger.error(f"Failed to update HubSpot contact: {e}")
            return {"success": False, "error": str(e)}

    async def upsert_contact_from_participant(
        self,
        access_token: str,
        participant_email: str,
        participant_name: str,
        company: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a Contact from a meeting participant.

        Args:
            access_token: Valid access token
            participant_email: Participant's email
            participant_name: Participant's full name
            company: Optional company name
            role: Optional job title/role

        Returns:
            Contact ID and whether it was created or updated
        """
        # Check if contact exists
        existing = await self.find_contact_by_email(access_token, participant_email)

        # Parse name
        name_parts = participant_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        contact_data = {
            "firstname": first_name,
            "lastname": last_name,
            "email": participant_email,
        }

        if role:
            contact_data["jobtitle"] = role
        if company:
            contact_data["company"] = company

        if existing:
            # Update existing contact (selective update)
            update_data = {}
            props = existing.get("properties", {})

            if role and not props.get("jobtitle"):
                update_data["jobtitle"] = role
            if company and not props.get("company"):
                update_data["company"] = company

            if update_data:
                result = await self.update_contact(access_token, existing["id"], update_data)
                result["action"] = "updated"
            else:
                result = {"success": True, "id": existing["id"], "action": "unchanged"}
        else:
            # Create new contact
            result = await self.create_contact(access_token, contact_data)
            result["action"] = "created"

        return result

    # =========================================================================
    # ENGAGEMENT LOGGING
    # =========================================================================

    async def log_meeting_engagement(
        self,
        access_token: str,
        contact_ids: List[str],
        meeting_title: str,
        meeting_date: datetime,
        duration_minutes: int,
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Log a meeting as an Engagement in HubSpot.

        Args:
            access_token: Valid access token
            contact_ids: List of HubSpot Contact IDs to associate
            meeting_title: Meeting subject/title
            meeting_date: When the meeting occurred
            duration_minutes: Meeting duration
            summary: Optional meeting summary
            key_points: Optional list of key points
            action_items: Optional list of action items

        Returns:
            Created engagement info
        """
        try:
            # Build body content
            body_parts = []
            if summary:
                body_parts.append(f"<strong>Summary:</strong><br>{summary}")
            if key_points:
                kp_html = "<br>".join(f"- {kp}" for kp in key_points)
                body_parts.append(f"<strong>Key Points:</strong><br>{kp_html}")
            if action_items:
                items_html = "<br>".join(
                    f"- {item.get('description', '')} (assigned to: {item.get('assignee', 'TBD')})"
                    for item in action_items
                )
                body_parts.append(f"<strong>Action Items:</strong><br>{items_html}")

            body = "<br><br>".join(body_parts) if body_parts else ""

            # Create meeting engagement
            engagement_data = {
                "properties": {
                    "hs_meeting_title": f"ReadIn AI: {meeting_title}",
                    "hs_meeting_body": body,
                    "hs_meeting_start_time": int(meeting_date.timestamp() * 1000),
                    "hs_meeting_end_time": int((meeting_date.timestamp() + duration_minutes * 60) * 1000),
                    "hs_meeting_outcome": "COMPLETED",
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 200,  # Meeting to Contact
                            }
                        ],
                    }
                    for contact_id in contact_ids
                ],
            }

            response = await self.client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/meetings",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=engagement_data,
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {"success": True, "id": data.get("id")}
            else:
                logger.error(f"HubSpot create meeting error: {data}")
                return {"success": False, "error": data.get("message", str(data))}

        except Exception as e:
            logger.error(f"Failed to log HubSpot engagement: {e}")
            return {"success": False, "error": str(e)}

    async def create_task(
        self,
        access_token: str,
        contact_id: str,
        subject: str,
        body: str,
        due_date: Optional[datetime] = None,
        priority: str = "MEDIUM",
    ) -> Dict[str, Any]:
        """
        Create a Task in HubSpot linked to a Contact.

        Args:
            access_token: Valid access token
            contact_id: Contact ID to link the task to
            subject: Task subject
            body: Task body/description
            due_date: Optional due date
            priority: Priority (HIGH, MEDIUM, LOW)

        Returns:
            Created task info
        """
        try:
            task_data = {
                "properties": {
                    "hs_task_subject": subject,
                    "hs_task_body": body,
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": priority,
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 204,  # Task to Contact
                            }
                        ],
                    }
                ],
            }

            if due_date:
                task_data["properties"]["hs_task_due_date"] = int(due_date.timestamp() * 1000)

            response = await self.client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/tasks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=task_data,
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {"success": True, "id": data.get("id")}
            else:
                logger.error(f"HubSpot create task error: {data}")
                return {"success": False, "error": data.get("message", str(data))}

        except Exception as e:
            logger.error(f"Failed to create HubSpot task: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # NOTES SYNC
    # =========================================================================

    async def create_note(
        self,
        access_token: str,
        contact_id: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Create a Note in HubSpot linked to a Contact.

        Args:
            access_token: Valid access token
            contact_id: Contact ID to link note to
            body: Note content

        Returns:
            Created note info
        """
        try:
            note_data = {
                "properties": {
                    "hs_note_body": body,
                    "hs_timestamp": int(datetime.utcnow().timestamp() * 1000),
                },
                "associations": [
                    {
                        "to": {"id": contact_id},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 202,  # Note to Contact
                            }
                        ],
                    }
                ],
            }

            response = await self.client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/notes",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=note_data,
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {"success": True, "id": data.get("id")}
            else:
                logger.error(f"HubSpot create note error: {data}")
                return {"success": False, "error": data.get("message", str(data))}

        except Exception as e:
            logger.error(f"Failed to create HubSpot note: {e}")
            return {"success": False, "error": str(e)}

    async def sync_meeting_notes(
        self,
        access_token: str,
        contact_id: str,
        meeting_title: str,
        meeting_date: datetime,
        notes: str,
    ) -> Dict[str, Any]:
        """
        Sync meeting notes to HubSpot as a Note.

        Args:
            access_token: Valid access token
            contact_id: Contact ID to link notes to
            meeting_title: Meeting title
            meeting_date: When the meeting occurred
            notes: Note content

        Returns:
            Created note info
        """
        formatted_body = f"""
<strong>Meeting Notes: {meeting_title}</strong><br>
<em>Date: {meeting_date.strftime('%B %d, %Y at %I:%M %p')}</em><br>
<br>
{notes.replace(chr(10), '<br>')}
"""
        return await self.create_note(access_token, contact_id, formatted_body)

    # =========================================================================
    # SYNC FULL MEETING
    # =========================================================================

    async def sync_meeting(
        self,
        access_token: str,
        meeting_title: str,
        meeting_date: datetime,
        duration_minutes: int,
        participants: List[Dict[str, str]],
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[Dict]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full sync of a meeting to HubSpot.

        Creates/updates contacts for all participants, logs the meeting engagement,
        syncs notes, and creates tasks for action items.

        Args:
            access_token: Valid access token
            meeting_title: Meeting title
            meeting_date: When the meeting occurred
            duration_minutes: Meeting duration
            participants: List of participant dicts with email, name, company, role
            summary: Optional meeting summary
            key_points: Optional list of key points
            action_items: Optional list of action items
            notes: Optional full meeting notes

        Returns:
            Sync results with contacts created/updated, engagements logged, etc.
        """
        results = {
            "contacts": [],
            "engagements": [],
            "tasks": [],
            "notes": [],
            "errors": [],
        }

        contact_ids = []

        # Process each participant
        for participant in participants:
            if not participant.get("email"):
                continue

            # Upsert contact
            contact_result = await self.upsert_contact_from_participant(
                access_token,
                participant["email"],
                participant.get("name", participant["email"]),
                participant.get("company"),
                participant.get("role"),
            )

            if contact_result.get("success"):
                contact_id = contact_result.get("id")
                contact_ids.append(contact_id)
                results["contacts"].append({
                    "email": participant["email"],
                    "id": contact_id,
                    "action": contact_result.get("action"),
                })

                # Sync notes if provided
                if notes:
                    notes_result = await self.sync_meeting_notes(
                        access_token,
                        contact_id,
                        meeting_title,
                        meeting_date,
                        notes,
                    )

                    if notes_result.get("success"):
                        results["notes"].append({
                            "contact_id": contact_id,
                            "note_id": notes_result.get("id"),
                        })
                    else:
                        results["errors"].append(f"Notes for {participant['email']}: {notes_result.get('error')}")

            else:
                results["errors"].append(f"Contact {participant['email']}: {contact_result.get('error')}")

        # Log meeting engagement with all contacts
        if contact_ids:
            engagement_result = await self.log_meeting_engagement(
                access_token,
                contact_ids,
                meeting_title,
                meeting_date,
                duration_minutes,
                summary,
                key_points,
                action_items,
            )

            if engagement_result.get("success"):
                results["engagements"].append({
                    "meeting_id": engagement_result.get("id"),
                    "contact_ids": contact_ids,
                })
            else:
                results["errors"].append(f"Meeting engagement: {engagement_result.get('error')}")

        # Create tasks for action items
        if action_items:
            for item in action_items:
                # Find contact for assignee if possible
                assignee_email = item.get("assignee_email")
                if assignee_email:
                    contact = await self.find_contact_by_email(access_token, assignee_email)
                    if contact:
                        priority = "HIGH" if item.get("priority") == "high" else "MEDIUM"
                        task_result = await self.create_task(
                            access_token,
                            contact["id"],
                            f"Action Item: {item.get('description', 'Task')[:80]}",
                            item.get("description", ""),
                            item.get("due_date"),
                            priority,
                        )

                        if task_result.get("success"):
                            results["tasks"].append({
                                "contact_id": contact["id"],
                                "task_id": task_result.get("id"),
                                "description": item.get("description"),
                            })
                        else:
                            results["errors"].append(f"Task: {task_result.get('error')}")

        results["success"] = len(results["errors"]) == 0
        return results

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_hubspot_configured() -> bool:
    """Check if HubSpot integration is configured."""
    return bool(HUBSPOT_CLIENT_ID and HUBSPOT_CLIENT_SECRET)
