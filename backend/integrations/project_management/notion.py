"""
Notion Integration for ReadIn AI.

Syncs action items to Notion databases as tasks/pages.

Notion API Documentation: https://developers.notion.com/

Features:
- OAuth 2.0 authentication
- Create tasks as database items
- Sync task status bidirectionally
- Support for due dates, priorities, and assignees
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

logger = logging.getLogger("notion")

# Configuration from environment
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID", "")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET", "")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI", "")


def is_notion_configured() -> bool:
    """Check if Notion integration is configured."""
    return bool(NOTION_CLIENT_ID and NOTION_CLIENT_SECRET)


class NotionIntegration(ProjectManagementIntegration):
    """
    Notion integration for syncing action items.

    Creates tasks as pages in a Notion database with properties for:
    - Title (title)
    - Status (select)
    - Priority (select)
    - Due Date (date)
    - Assignee (rich_text or people)
    - Meeting (rich_text)
    - ReadIn ID (number) - for linking back
    """

    PROVIDER_NAME = "notion"
    DISPLAY_NAME = "Notion"
    OAUTH_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
    OAUTH_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
    API_BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    # Property name mappings - can be customized per user
    DEFAULT_PROPERTY_NAMES = {
        "title": "Name",
        "status": "Status",
        "priority": "Priority",
        "due_date": "Due Date",
        "assignee": "Assignee",
        "description": "Description",
        "meeting": "Meeting",
        "readin_id": "ReadIn ID",
    }

    # Default status options
    STATUS_MAPPING = {
        TaskStatus.PENDING: "Not Started",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.CANCELLED: "Cancelled",
    }

    REVERSE_STATUS_MAPPING = {
        "Not Started": TaskStatus.PENDING,
        "To Do": TaskStatus.PENDING,
        "In Progress": TaskStatus.IN_PROGRESS,
        "In progress": TaskStatus.IN_PROGRESS,
        "Done": TaskStatus.COMPLETED,
        "Complete": TaskStatus.COMPLETED,
        "Completed": TaskStatus.COMPLETED,
        "Cancelled": TaskStatus.CANCELLED,
        "Canceled": TaskStatus.CANCELLED,
    }

    # Priority options
    PRIORITY_MAPPING = {
        TaskPriority.LOW: "Low",
        TaskPriority.MEDIUM: "Medium",
        TaskPriority.HIGH: "High",
        TaskPriority.URGENT: "Urgent",
    }

    REVERSE_PRIORITY_MAPPING = {
        "Low": TaskPriority.LOW,
        "Medium": TaskPriority.MEDIUM,
        "High": TaskPriority.HIGH,
        "Urgent": TaskPriority.URGENT,
    }

    def __init__(
        self,
        db,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        super().__init__(db, access_token, refresh_token)
        self.database_id = database_id
        self.property_names = self.DEFAULT_PROPERTY_NAMES.copy()

    def _get_default_headers(self) -> Dict[str, str]:
        """Get Notion-specific headers."""
        headers = {
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """Generate Notion OAuth authorization URL."""
        params = {
            "client_id": NOTION_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": str(user_id),
        }
        return f"{self.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        import base64

        # Notion uses Basic Auth for token exchange
        credentials = base64.b64encode(
            f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}".encode()
        ).decode()

        try:
            response = await self.client.post(
                self.OAUTH_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/json",
                },
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error(f"Notion token exchange failed: {response.text}")
                return {"success": False, "error": response.text}

            data = response.json()

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "workspace_id": data.get("workspace_id"),
                "workspace_name": data.get("workspace_name"),
                "workspace_icon": data.get("workspace_icon"),
                "bot_id": data.get("bot_id"),
                "owner": data.get("owner"),
                "duplicated_template_id": data.get("duplicated_template_id"),
            }

        except Exception as e:
            logger.error(f"Notion OAuth error: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> Optional[str]:
        """
        Notion tokens don't expire and don't have refresh tokens.
        Return the existing access token.
        """
        return self.access_token

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_task(self, task: TaskData) -> SyncResult:
        """Create a task as a Notion database page."""
        if not self.database_id:
            return SyncResult(
                success=False,
                error="No database ID configured. Please select a database first."
            )

        try:
            # Build properties based on task data
            properties = self._build_properties(task)

            # Create the page
            response = await self.client.post(
                f"{self.API_BASE_URL}/pages",
                json={
                    "parent": {"database_id": self.database_id},
                    "properties": properties,
                    "children": self._build_page_content(task),
                },
            )

            if response.status_code != 200:
                logger.error(f"Notion create task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            data = response.json()

            return SyncResult(
                success=True,
                external_id=data.get("id"),
                external_url=data.get("url"),
                metadata={
                    "notion_id": data.get("id"),
                    "created_time": data.get("created_time"),
                }
            )

        except Exception as e:
            logger.error(f"Error creating Notion task: {e}")
            return SyncResult(success=False, error=str(e))

    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """Update an existing Notion page."""
        try:
            properties = self._build_properties(task)

            response = await self.client.patch(
                f"{self.API_BASE_URL}/pages/{external_id}",
                json={"properties": properties},
            )

            if response.status_code != 200:
                logger.error(f"Notion update task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            data = response.json()

            return SyncResult(
                success=True,
                external_id=data.get("id"),
                external_url=data.get("url"),
            )

        except Exception as e:
            logger.error(f"Error updating Notion task: {e}")
            return SyncResult(success=False, error=str(e))

    async def delete_task(self, external_id: str) -> SyncResult:
        """Archive a Notion page (Notion doesn't permanently delete via API)."""
        try:
            response = await self.client.patch(
                f"{self.API_BASE_URL}/pages/{external_id}",
                json={"archived": True},
            )

            if response.status_code != 200:
                logger.error(f"Notion delete task failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            return SyncResult(success=True, external_id=external_id)

        except Exception as e:
            logger.error(f"Error deleting Notion task: {e}")
            return SyncResult(success=False, error=str(e))

    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """Get the current status from Notion."""
        task_data = await self.get_task(external_id)
        if not task_data:
            return None

        # Extract status from properties
        properties = task_data.get("properties", {})
        status_prop = properties.get(self.property_names["status"], {})

        if status_prop.get("type") == "select":
            status_name = status_prop.get("select", {}).get("name", "")
            return self.REVERSE_STATUS_MAPPING.get(status_name, TaskStatus.PENDING)
        elif status_prop.get("type") == "status":
            status_name = status_prop.get("status", {}).get("name", "")
            return self.REVERSE_STATUS_MAPPING.get(status_name, TaskStatus.PENDING)

        return TaskStatus.PENDING

    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get task details from Notion."""
        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/pages/{external_id}",
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"Notion get task failed: {response.text}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Error getting Notion task: {e}")
            return None

    # =========================================================================
    # WORKSPACE/DATABASE METHODS
    # =========================================================================

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List workspaces - Notion returns workspace info in OAuth response.
        For already connected users, we return the search results as workspace context.
        """
        try:
            # Search for any accessible databases as a proxy for workspace access
            response = await self.client.post(
                f"{self.API_BASE_URL}/search",
                json={
                    "query": "",
                    "filter": {"property": "object", "value": "database"},
                    "page_size": 1,
                },
            )

            if response.status_code != 200:
                return []

            # If we can search, the workspace is accessible
            return [{"id": "current", "name": "Connected Workspace"}]

        except Exception as e:
            logger.error(f"Error listing Notion workspaces: {e}")
            return []

    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List available databases that can be used for task sync."""
        try:
            response = await self.client.post(
                f"{self.API_BASE_URL}/search",
                json={
                    "query": "",
                    "filter": {"property": "object", "value": "database"},
                    "page_size": 100,
                },
            )

            if response.status_code != 200:
                logger.error(f"Notion search databases failed: {response.text}")
                return []

            data = response.json()
            databases = []

            for db in data.get("results", []):
                # Get the database title
                title_prop = db.get("title", [])
                title = "Untitled"
                if title_prop:
                    title = "".join([t.get("plain_text", "") for t in title_prop])

                databases.append({
                    "id": db.get("id"),
                    "name": title,
                    "url": db.get("url"),
                    "icon": db.get("icon"),
                    "properties": list(db.get("properties", {}).keys()),
                })

            return databases

        except Exception as e:
            logger.error(f"Error listing Notion databases: {e}")
            return []

    async def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Get the schema/properties of a database."""
        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/databases/{database_id}",
            )

            if response.status_code != 200:
                logger.error(f"Notion get database failed: {response.text}")
                return {}

            return response.json()

        except Exception as e:
            logger.error(f"Error getting Notion database: {e}")
            return {}

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _build_properties(self, task: TaskData) -> Dict[str, Any]:
        """Build Notion properties from TaskData."""
        properties = {}

        # Title (required)
        properties[self.property_names["title"]] = {
            "title": [{"text": {"content": task.title}}]
        }

        # Status
        status_value = self.STATUS_MAPPING.get(task.status, "Not Started")
        properties[self.property_names["status"]] = {
            "select": {"name": status_value}
        }

        # Priority
        priority_value = self.PRIORITY_MAPPING.get(task.priority, "Medium")
        properties[self.property_names["priority"]] = {
            "select": {"name": priority_value}
        }

        # Due Date
        if task.due_date:
            properties[self.property_names["due_date"]] = {
                "date": {"start": task.due_date.strftime("%Y-%m-%d")}
            }

        # Assignee (as rich text since we may not have Notion user IDs)
        if task.assignee:
            properties[self.property_names["assignee"]] = {
                "rich_text": [{"text": {"content": task.assignee}}]
            }

        # Meeting reference
        if task.meeting_title:
            properties[self.property_names["meeting"]] = {
                "rich_text": [{"text": {"content": task.meeting_title}}]
            }

        # ReadIn ID for linking
        properties[self.property_names["readin_id"]] = {
            "number": task.id
        }

        return properties

    def _build_page_content(self, task: TaskData) -> List[Dict[str, Any]]:
        """Build the page content blocks."""
        blocks = []

        # Add description as a paragraph
        if task.description:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": task.description}}]
                }
            })

        # Add metadata section
        metadata_text = f"Created from ReadIn AI - Action Item #{task.id}"
        if task.meeting_title:
            metadata_text += f"\nMeeting: {task.meeting_title}"

        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "📝"},
                "rich_text": [{"text": {"content": metadata_text}}]
            }
        })

        return blocks

    def map_status_to_external(self, status: TaskStatus) -> str:
        """Map internal status to Notion status name."""
        return self.STATUS_MAPPING.get(status, "Not Started")

    def map_status_from_external(self, external_status: str) -> TaskStatus:
        """Map Notion status to internal status."""
        return self.REVERSE_STATUS_MAPPING.get(external_status, TaskStatus.PENDING)

    def map_priority_to_external(self, priority: TaskPriority) -> str:
        """Map internal priority to Notion priority name."""
        return self.PRIORITY_MAPPING.get(priority, "Medium")

    def map_priority_from_external(self, external_priority: str) -> TaskPriority:
        """Map Notion priority to internal priority."""
        return self.REVERSE_PRIORITY_MAPPING.get(external_priority, TaskPriority.MEDIUM)
