"""
Asana Integration for ReadIn AI.

Syncs action items to Asana as tasks within projects.

Asana API Documentation: https://developers.asana.com/docs

Features:
- OAuth 2.0 authentication
- Create tasks in projects
- Sync task status bidirectionally
- Support for due dates, priorities, assignees, and tags
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from integrations.project_management.base import (
    ProjectManagementIntegration,
    TaskData,
    TaskStatus,
    TaskPriority,
    SyncResult,
)

logger = logging.getLogger("asana")

# Configuration from environment
ASANA_CLIENT_ID = os.getenv("ASANA_CLIENT_ID", "")
ASANA_CLIENT_SECRET = os.getenv("ASANA_CLIENT_SECRET", "")
ASANA_REDIRECT_URI = os.getenv("ASANA_REDIRECT_URI", "")


def is_asana_configured() -> bool:
    """Check if Asana integration is configured."""
    return bool(ASANA_CLIENT_ID and ASANA_CLIENT_SECRET)


class AsanaIntegration(ProjectManagementIntegration):
    """
    Asana integration for syncing action items.

    Creates tasks in Asana projects with:
    - Name/Title
    - Notes (description)
    - Due Date
    - Assignee
    - Custom fields for Priority and ReadIn ID
    - Tags for categorization
    """

    PROVIDER_NAME = "asana"
    DISPLAY_NAME = "Asana"
    OAUTH_AUTHORIZE_URL = "https://app.asana.com/-/oauth_authorize"
    OAUTH_TOKEN_URL = "https://app.asana.com/-/oauth_token"
    API_BASE_URL = "https://app.asana.com/api/1.0"

    # Status mapping - Asana uses sections or custom fields for status
    STATUS_MAPPING = {
        TaskStatus.PENDING: "To Do",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.COMPLETED: "completed",  # Asana uses completed boolean
        TaskStatus.CANCELLED: "cancelled",
    }

    REVERSE_STATUS_MAPPING = {
        "To Do": TaskStatus.PENDING,
        "In Progress": TaskStatus.IN_PROGRESS,
        "Done": TaskStatus.COMPLETED,
        "Completed": TaskStatus.COMPLETED,
    }

    def __init__(
        self,
        db,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        workspace_gid: Optional[str] = None,
        project_gid: Optional[str] = None,
    ):
        super().__init__(db, access_token, refresh_token)
        self.workspace_gid = workspace_gid
        self.project_gid = project_gid

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """Generate Asana OAuth authorization URL."""
        params = {
            "client_id": ASANA_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": str(user_id),
            "scope": "default",
        }
        return f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            response = await self.client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": ASANA_CLIENT_ID,
                    "client_secret": ASANA_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Asana token exchange failed: {response.text}")
                return {"success": False, "error": response.text}

            data = response.json()

            # Get user info
            user_info = data.get("data", {})

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "token_type": data.get("token_type"),
                "user_gid": user_info.get("gid"),
                "user_email": user_info.get("email"),
                "user_name": user_info.get("name"),
            }

        except Exception as e:
            logger.error(f"Asana OAuth error: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> Optional[str]:
        """Refresh the Asana access token."""
        if not self.refresh_token:
            return None

        try:
            response = await self.client.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": ASANA_CLIENT_ID,
                    "client_secret": ASANA_CLIENT_SECRET,
                    "refresh_token": self.refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Asana token refresh failed: {response.text}")
                return None

            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token", self.refresh_token)

            return self.access_token

        except Exception as e:
            logger.error(f"Asana token refresh error: {e}")
            return None

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_task(self, task: TaskData) -> SyncResult:
        """Create a task in Asana."""
        if not self.project_gid:
            return SyncResult(
                success=False,
                error="No project selected. Please select an Asana project first."
            )

        try:
            # Build task data
            task_data = self._build_task_data(task)

            response = await self.client.post(
                f"{self.API_BASE_URL}/tasks",
                json={"data": task_data},
            )

            if response.status_code not in (200, 201):
                logger.error(f"Asana create task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            data = response.json().get("data", {})

            return SyncResult(
                success=True,
                external_id=data.get("gid"),
                external_url=data.get("permalink_url"),
                metadata={
                    "asana_gid": data.get("gid"),
                    "created_at": data.get("created_at"),
                }
            )

        except Exception as e:
            logger.error(f"Error creating Asana task: {e}")
            return SyncResult(success=False, error=str(e))

    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """Update an existing Asana task."""
        try:
            task_data = self._build_task_data(task, is_update=True)

            response = await self.client.put(
                f"{self.API_BASE_URL}/tasks/{external_id}",
                json={"data": task_data},
            )

            if response.status_code != 200:
                logger.error(f"Asana update task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            data = response.json().get("data", {})

            return SyncResult(
                success=True,
                external_id=data.get("gid"),
                external_url=data.get("permalink_url"),
            )

        except Exception as e:
            logger.error(f"Error updating Asana task: {e}")
            return SyncResult(success=False, error=str(e))

    async def delete_task(self, external_id: str) -> SyncResult:
        """Delete an Asana task."""
        try:
            response = await self.client.delete(
                f"{self.API_BASE_URL}/tasks/{external_id}",
            )

            if response.status_code not in (200, 204):
                logger.error(f"Asana delete task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            return SyncResult(success=True, external_id=external_id)

        except Exception as e:
            logger.error(f"Error deleting Asana task: {e}")
            return SyncResult(success=False, error=str(e))

    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """Get the current status from Asana."""
        task_data = await self.get_task(external_id)
        if not task_data:
            return None

        # Check if completed
        if task_data.get("completed"):
            return TaskStatus.COMPLETED

        # Check memberships for section-based status
        memberships = task_data.get("memberships", [])
        for membership in memberships:
            section = membership.get("section", {})
            section_name = section.get("name", "")
            if section_name in self.REVERSE_STATUS_MAPPING:
                return self.REVERSE_STATUS_MAPPING[section_name]

        return TaskStatus.PENDING

    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get task details from Asana."""
        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/tasks/{external_id}",
                params={
                    "opt_fields": "name,notes,completed,due_on,assignee,memberships.section.name,permalink_url,tags.name"
                },
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"Asana get task failed: {response.text}")
                return None

            return response.json().get("data")

        except Exception as e:
            logger.error(f"Error getting Asana task: {e}")
            return None

    # =========================================================================
    # WORKSPACE/PROJECT METHODS
    # =========================================================================

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List Asana workspaces the user has access to."""
        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/workspaces",
                params={"opt_fields": "name,gid"},
            )

            if response.status_code != 200:
                logger.error(f"Asana list workspaces failed: {response.text}")
                return []

            data = response.json().get("data", [])
            return [
                {
                    "id": ws.get("gid"),
                    "name": ws.get("name"),
                }
                for ws in data
            ]

        except Exception as e:
            logger.error(f"Error listing Asana workspaces: {e}")
            return []

    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List projects in a workspace."""
        workspace_gid = workspace_id or self.workspace_gid
        if not workspace_gid:
            return []

        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/workspaces/{workspace_gid}/projects",
                params={
                    "opt_fields": "name,gid,color,permalink_url,archived",
                    "archived": "false",
                },
            )

            if response.status_code != 200:
                logger.error(f"Asana list projects failed: {response.text}")
                return []

            data = response.json().get("data", [])
            return [
                {
                    "id": proj.get("gid"),
                    "name": proj.get("name"),
                    "url": proj.get("permalink_url"),
                    "color": proj.get("color"),
                }
                for proj in data
            ]

        except Exception as e:
            logger.error(f"Error listing Asana projects: {e}")
            return []

    async def list_sections(self, project_gid: Optional[str] = None) -> List[Dict[str, Any]]:
        """List sections in a project (used for status)."""
        project = project_gid or self.project_gid
        if not project:
            return []

        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/projects/{project}/sections",
                params={"opt_fields": "name,gid"},
            )

            if response.status_code != 200:
                logger.error(f"Asana list sections failed: {response.text}")
                return []

            data = response.json().get("data", [])
            return [
                {
                    "id": section.get("gid"),
                    "name": section.get("name"),
                }
                for section in data
            ]

        except Exception as e:
            logger.error(f"Error listing Asana sections: {e}")
            return []

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find an Asana user by email for assignee mapping."""
        if not self.workspace_gid:
            return None

        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/workspaces/{self.workspace_gid}/users",
                params={"opt_fields": "name,email,gid"},
            )

            if response.status_code != 200:
                return None

            data = response.json().get("data", [])
            for user in data:
                if user.get("email", "").lower() == email.lower():
                    return user

            return None

        except Exception as e:
            logger.error(f"Error finding Asana user: {e}")
            return None

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _build_task_data(
        self,
        task: TaskData,
        is_update: bool = False,
    ) -> Dict[str, Any]:
        """Build Asana task data from TaskData."""
        data = {
            "name": task.title,
            "notes": self._build_notes(task),
        }

        # Only set project on create
        if not is_update and self.project_gid:
            data["projects"] = [self.project_gid]

        # Due date
        if task.due_date:
            data["due_on"] = task.due_date.strftime("%Y-%m-%d")

        # Completed status
        data["completed"] = task.status == TaskStatus.COMPLETED

        return data

    def _build_notes(self, task: TaskData) -> str:
        """Build the notes/description field."""
        notes_parts = []

        if task.description:
            notes_parts.append(task.description)

        notes_parts.append("")
        notes_parts.append("---")
        notes_parts.append(f"ReadIn AI Action Item #{task.id}")

        if task.meeting_title:
            notes_parts.append(f"Meeting: {task.meeting_title}")

        if task.assignee:
            notes_parts.append(f"Assigned to: {task.assignee}")

        priority_text = task.priority.value.title()
        notes_parts.append(f"Priority: {priority_text}")

        return "\n".join(notes_parts)

    async def move_to_section(self, task_gid: str, section_gid: str) -> bool:
        """Move a task to a specific section (for status changes)."""
        try:
            response = await self.client.post(
                f"{self.API_BASE_URL}/sections/{section_gid}/addTask",
                json={"data": {"task": task_gid}},
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error moving Asana task to section: {e}")
            return False

    async def add_tag(self, task_gid: str, tag_gid: str) -> bool:
        """Add a tag to a task."""
        try:
            response = await self.client.post(
                f"{self.API_BASE_URL}/tasks/{task_gid}/addTag",
                json={"data": {"tag": tag_gid}},
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error adding tag to Asana task: {e}")
            return False

    async def find_or_create_tag(
        self,
        name: str,
        workspace_gid: Optional[str] = None,
    ) -> Optional[str]:
        """Find a tag by name or create it."""
        workspace = workspace_gid or self.workspace_gid
        if not workspace:
            return None

        try:
            # Search for existing tag
            response = await self.client.get(
                f"{self.API_BASE_URL}/workspaces/{workspace}/tags",
                params={"opt_fields": "name,gid"},
            )

            if response.status_code == 200:
                tags = response.json().get("data", [])
                for tag in tags:
                    if tag.get("name", "").lower() == name.lower():
                        return tag.get("gid")

            # Create new tag
            response = await self.client.post(
                f"{self.API_BASE_URL}/workspaces/{workspace}/tags",
                json={"data": {"name": name}},
            )

            if response.status_code in (200, 201):
                return response.json().get("data", {}).get("gid")

            return None

        except Exception as e:
            logger.error(f"Error finding/creating Asana tag: {e}")
            return None
