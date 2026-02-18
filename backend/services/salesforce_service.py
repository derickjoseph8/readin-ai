"""
Salesforce CRM Integration Service for ReadIn AI.

Provides:
- OAuth 2.0 authentication with Salesforce
- Create/update Contact records from meeting participants
- Log meeting activities
- Sync meeting notes to Salesforce
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from config import (
    SALESFORCE_CLIENT_ID,
    SALESFORCE_CLIENT_SECRET,
    APP_URL,
)

logger = logging.getLogger("salesforce")

# Salesforce API endpoints
SALESFORCE_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_USERINFO_URL = "/services/oauth2/userinfo"


@dataclass
class SalesforceConnection:
    """Represents a connected Salesforce org."""
    instance_url: str
    access_token: str
    refresh_token: str
    user_id: str
    org_id: str
    display_name: Optional[str] = None


class SalesforceService:
    """
    Salesforce CRM integration service for ReadIn AI.

    Handles OAuth, contact management, and activity logging.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    # =========================================================================
    # OAUTH FLOW
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate Salesforce OAuth authorization URL.

        Args:
            user_id: User initiating the connection
            redirect_uri: Callback URL after authorization

        Returns:
            OAuth authorization URL
        """
        scopes = [
            "api",
            "refresh_token",
            "offline_access",
            "id",
            "profile",
            "email",
        ]

        state = f"{user_id}:{int(time.time())}"

        params = {
            "response_type": "code",
            "client_id": SALESFORCE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{SALESFORCE_AUTH_URL}?{query}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Token response with access_token, refresh_token, instance_url, etc.
        """
        try:
            response = await self.client.post(
                SALESFORCE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": SALESFORCE_CLIENT_ID,
                    "client_secret": SALESFORCE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Salesforce OAuth error: {data.get('error_description')}")
                return {"success": False, "error": data.get("error_description")}

            # Get user info
            instance_url = data.get("instance_url")
            access_token = data.get("access_token")

            user_info = await self._get_user_info(instance_url, access_token)

            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": data.get("refresh_token"),
                "instance_url": instance_url,
                "user_id": data.get("id", "").split("/")[-1],
                "org_id": user_info.get("organization_id"),
                "display_name": user_info.get("display_name"),
                "email": user_info.get("email"),
            }

        except Exception as e:
            logger.error(f"Salesforce OAuth exchange failed: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_token(self, refresh_token: str, instance_url: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token
            instance_url: The Salesforce instance URL

        Returns:
            New token data
        """
        try:
            response = await self.client.post(
                SALESFORCE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": SALESFORCE_CLIENT_ID,
                    "client_secret": SALESFORCE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                },
            )

            data = response.json()

            if "error" in data:
                logger.error(f"Salesforce token refresh error: {data.get('error_description')}")
                return {"success": False, "error": data.get("error_description")}

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "instance_url": data.get("instance_url", instance_url),
            }

        except Exception as e:
            logger.error(f"Salesforce token refresh failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_info(self, instance_url: str, access_token: str) -> Dict[str, Any]:
        """Get current user information from Salesforce."""
        try:
            response = await self.client.get(
                f"{instance_url}{SALESFORCE_USERINFO_URL}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Salesforce user info: {e}")
            return {}

    # =========================================================================
    # CONTACT MANAGEMENT
    # =========================================================================

    async def find_contact_by_email(
        self,
        instance_url: str,
        access_token: str,
        email: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a Contact in Salesforce by email address.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            email: Email address to search

        Returns:
            Contact record or None
        """
        try:
            query = f"SELECT Id, FirstName, LastName, Email, Title, Account.Name FROM Contact WHERE Email = '{email}' LIMIT 1"

            response = await self.client.get(
                f"{instance_url}/services/data/v58.0/query",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": query},
            )

            data = response.json()

            if data.get("totalSize", 0) > 0:
                return data["records"][0]
            return None

        except Exception as e:
            logger.error(f"Failed to find Salesforce contact: {e}")
            return None

    async def create_contact(
        self,
        instance_url: str,
        access_token: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new Contact in Salesforce.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            contact_data: Contact fields (FirstName, LastName, Email, etc.)

        Returns:
            Created contact info including Id
        """
        try:
            response = await self.client.post(
                f"{instance_url}/services/data/v58.0/sobjects/Contact",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=contact_data,
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "id": data.get("id"),
                }
            else:
                logger.error(f"Salesforce create contact error: {data}")
                return {"success": False, "error": str(data)}

        except Exception as e:
            logger.error(f"Failed to create Salesforce contact: {e}")
            return {"success": False, "error": str(e)}

    async def update_contact(
        self,
        instance_url: str,
        access_token: str,
        contact_id: str,
        contact_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing Contact in Salesforce.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            contact_id: Salesforce Contact ID
            contact_data: Fields to update

        Returns:
            Success status
        """
        try:
            response = await self.client.patch(
                f"{instance_url}/services/data/v58.0/sobjects/Contact/{contact_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=contact_data,
            )

            if response.status_code == 204:
                return {"success": True, "id": contact_id}
            else:
                data = response.json()
                logger.error(f"Salesforce update contact error: {data}")
                return {"success": False, "error": str(data)}

        except Exception as e:
            logger.error(f"Failed to update Salesforce contact: {e}")
            return {"success": False, "error": str(e)}

    async def upsert_contact_from_participant(
        self,
        instance_url: str,
        access_token: str,
        participant_email: str,
        participant_name: str,
        company: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a Contact from a meeting participant.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            participant_email: Participant's email
            participant_name: Participant's full name
            company: Optional company name
            role: Optional job title/role

        Returns:
            Contact ID and whether it was created or updated
        """
        # Check if contact exists
        existing = await self.find_contact_by_email(instance_url, access_token, participant_email)

        # Parse name
        name_parts = participant_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        contact_data = {
            "FirstName": first_name,
            "LastName": last_name or "(Unknown)",
            "Email": participant_email,
        }

        if role:
            contact_data["Title"] = role

        if existing:
            # Update existing contact (don't overwrite all fields)
            update_data = {}
            if role and not existing.get("Title"):
                update_data["Title"] = role

            if update_data:
                result = await self.update_contact(
                    instance_url, access_token, existing["Id"], update_data
                )
                result["action"] = "updated"
            else:
                result = {"success": True, "id": existing["Id"], "action": "unchanged"}
        else:
            # Create new contact
            result = await self.create_contact(instance_url, access_token, contact_data)
            result["action"] = "created"

        return result

    # =========================================================================
    # ACTIVITY LOGGING
    # =========================================================================

    async def log_meeting_activity(
        self,
        instance_url: str,
        access_token: str,
        contact_id: str,
        meeting_title: str,
        meeting_date: datetime,
        duration_minutes: int,
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Log a meeting as an Event in Salesforce linked to a Contact.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            contact_id: Contact ID to link the activity to
            meeting_title: Meeting subject/title
            meeting_date: When the meeting occurred
            duration_minutes: Meeting duration
            summary: Optional meeting summary
            key_points: Optional list of key points
            action_items: Optional list of action items

        Returns:
            Created event info
        """
        try:
            # Build description
            description_parts = []
            if summary:
                description_parts.append(f"Summary:\n{summary}")
            if key_points:
                description_parts.append("\nKey Points:\n" + "\n".join(f"- {kp}" for kp in key_points))
            if action_items:
                items_text = "\n".join(
                    f"- {item.get('description', '')} (assigned to: {item.get('assignee', 'TBD')})"
                    for item in action_items
                )
                description_parts.append(f"\nAction Items:\n{items_text}")

            description = "\n".join(description_parts) if description_parts else None

            # Create Event (Meeting)
            event_data = {
                "Subject": f"ReadIn AI: {meeting_title}",
                "WhoId": contact_id,  # Link to Contact
                "StartDateTime": meeting_date.isoformat(),
                "EndDateTime": (meeting_date.replace(minute=meeting_date.minute + duration_minutes)).isoformat(),
                "DurationInMinutes": duration_minutes,
                "Type": "Meeting",
                "Description": description,
            }

            response = await self.client.post(
                f"{instance_url}/services/data/v58.0/sobjects/Event",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=event_data,
            )

            data = response.json()

            if response.status_code in [200, 201]:
                return {"success": True, "id": data.get("id")}
            else:
                logger.error(f"Salesforce create event error: {data}")
                return {"success": False, "error": str(data)}

        except Exception as e:
            logger.error(f"Failed to log Salesforce activity: {e}")
            return {"success": False, "error": str(e)}

    async def create_task(
        self,
        instance_url: str,
        access_token: str,
        contact_id: str,
        subject: str,
        description: str,
        due_date: Optional[datetime] = None,
        priority: str = "Normal",
    ) -> Dict[str, Any]:
        """
        Create a Task in Salesforce linked to a Contact.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            contact_id: Contact ID to link the task to
            subject: Task subject
            description: Task description
            due_date: Optional due date
            priority: Priority (High, Normal, Low)

        Returns:
            Created task info
        """
        try:
            task_data = {
                "Subject": subject,
                "WhoId": contact_id,
                "Description": description,
                "Priority": priority,
                "Status": "Not Started",
            }

            if due_date:
                task_data["ActivityDate"] = due_date.strftime("%Y-%m-%d")

            response = await self.client.post(
                f"{instance_url}/services/data/v58.0/sobjects/Task",
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
                logger.error(f"Salesforce create task error: {data}")
                return {"success": False, "error": str(data)}

        except Exception as e:
            logger.error(f"Failed to create Salesforce task: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # NOTES SYNC
    # =========================================================================

    async def sync_meeting_notes(
        self,
        instance_url: str,
        access_token: str,
        contact_id: str,
        meeting_title: str,
        meeting_date: datetime,
        notes: str,
    ) -> Dict[str, Any]:
        """
        Create a ContentNote in Salesforce linked to a Contact.

        Args:
            instance_url: Salesforce instance URL
            access_token: Valid access token
            contact_id: Contact ID to link notes to
            meeting_title: Meeting title for the note title
            meeting_date: When the meeting occurred
            notes: Note content

        Returns:
            Created note info
        """
        try:
            import base64

            # Create ContentNote
            note_data = {
                "Title": f"Meeting Notes: {meeting_title} - {meeting_date.strftime('%Y-%m-%d')}",
                "Content": base64.b64encode(notes.encode()).decode(),
            }

            response = await self.client.post(
                f"{instance_url}/services/data/v58.0/sobjects/ContentNote",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=note_data,
            )

            data = response.json()

            if response.status_code not in [200, 201]:
                logger.error(f"Salesforce create note error: {data}")
                return {"success": False, "error": str(data)}

            note_id = data.get("id")

            # Link note to Contact via ContentDocumentLink
            link_data = {
                "ContentDocumentId": note_id,
                "LinkedEntityId": contact_id,
                "ShareType": "V",  # Viewer permission
            }

            link_response = await self.client.post(
                f"{instance_url}/services/data/v58.0/sobjects/ContentDocumentLink",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=link_data,
            )

            if link_response.status_code in [200, 201]:
                return {"success": True, "id": note_id}
            else:
                link_data = link_response.json()
                logger.error(f"Salesforce link note error: {link_data}")
                return {"success": False, "error": str(link_data)}

        except Exception as e:
            logger.error(f"Failed to sync Salesforce notes: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # SYNC FULL MEETING
    # =========================================================================

    async def sync_meeting(
        self,
        instance_url: str,
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
        Full sync of a meeting to Salesforce.

        Creates/updates contacts for all participants, logs the meeting activity,
        syncs notes, and creates tasks for action items.

        Args:
            instance_url: Salesforce instance URL
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
            Sync results with contacts created/updated, activities logged, etc.
        """
        results = {
            "contacts": [],
            "activities": [],
            "tasks": [],
            "notes": [],
            "errors": [],
        }

        # Process each participant
        for participant in participants:
            if not participant.get("email"):
                continue

            # Upsert contact
            contact_result = await self.upsert_contact_from_participant(
                instance_url,
                access_token,
                participant["email"],
                participant.get("name", participant["email"]),
                participant.get("company"),
                participant.get("role"),
            )

            if contact_result.get("success"):
                contact_id = contact_result.get("id")
                results["contacts"].append({
                    "email": participant["email"],
                    "id": contact_id,
                    "action": contact_result.get("action"),
                })

                # Log meeting activity
                activity_result = await self.log_meeting_activity(
                    instance_url,
                    access_token,
                    contact_id,
                    meeting_title,
                    meeting_date,
                    duration_minutes,
                    summary,
                    key_points,
                    action_items,
                )

                if activity_result.get("success"):
                    results["activities"].append({
                        "contact_id": contact_id,
                        "event_id": activity_result.get("id"),
                    })
                else:
                    results["errors"].append(f"Activity for {participant['email']}: {activity_result.get('error')}")

                # Sync notes if provided
                if notes:
                    notes_result = await self.sync_meeting_notes(
                        instance_url,
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

        # Create tasks for action items
        if action_items:
            for item in action_items:
                # Find contact for assignee if possible
                assignee_email = item.get("assignee_email")
                if assignee_email:
                    contact = await self.find_contact_by_email(instance_url, access_token, assignee_email)
                    if contact:
                        task_result = await self.create_task(
                            instance_url,
                            access_token,
                            contact["Id"],
                            f"Action Item: {item.get('description', 'Task')[:80]}",
                            item.get("description", ""),
                            item.get("due_date"),
                            "High" if item.get("priority") == "high" else "Normal",
                        )

                        if task_result.get("success"):
                            results["tasks"].append({
                                "contact_id": contact["Id"],
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

def is_salesforce_configured() -> bool:
    """Check if Salesforce integration is configured."""
    return bool(SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET)
