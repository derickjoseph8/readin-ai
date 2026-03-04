"""
Jira Integration for ReadIn AI.

Syncs action items to Jira as issues.

Jira Cloud API Documentation: https://developer.atlassian.com/cloud/jira/platform/

Features:
- OAuth 2.0 authentication (Atlassian Connect)
- Create issues from action items
- Sync issue status bidirectionally
- Support for due dates, priorities, assignees, and labels
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

logger = logging.getLogger("jira")

# Configuration from environment
JIRA_CLIENT_ID = os.getenv("JIRA_CLIENT_ID", "")
JIRA_CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET", "")
JIRA_REDIRECT_URI = os.getenv("JIRA_REDIRECT_URI", "")


def is_jira_configured() -> bool:
    """Check if Jira integration is configured."""
    return bool(JIRA_CLIENT_ID and JIRA_CLIENT_SECRET)


class JiraIntegration(ProjectManagementIntegration):
    """
    Jira integration for syncing action items.

    Creates issues in Jira with:
    - Summary (title)
    - Description
    - Issue Type (Task)
    - Priority
    - Due Date
    - Assignee
    - Labels
    """

    PROVIDER_NAME = "jira"
    DISPLAY_NAME = "Jira"
    OAUTH_AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
    OAUTH_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    API_BASE_URL = "https://api.atlassian.com"

    # Jira has configurable priorities, these are defaults
    # Priority IDs: 1=Highest, 2=High, 3=Medium, 4=Low, 5=Lowest
    PRIORITY_MAPPING = {
        TaskPriority.URGENT: "1",  # Highest
        TaskPriority.HIGH: "2",
        TaskPriority.MEDIUM: "3",
        TaskPriority.LOW: "4",
    }

    REVERSE_PRIORITY_MAPPING = {
        "Highest": TaskPriority.URGENT,
        "High": TaskPriority.HIGH,
        "Medium": TaskPriority.MEDIUM,
        "Low": TaskPriority.LOW,
        "Lowest": TaskPriority.LOW,
    }

    # Common Jira status category mappings
    STATUS_CATEGORY_MAPPING = {
        "new": TaskStatus.PENDING,
        "indeterminate": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.COMPLETED,
    }

    def __init__(
        self,
        db,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        cloud_id: Optional[str] = None,
        project_key: Optional[str] = None,
    ):
        super().__init__(db, access_token, refresh_token)
        self.cloud_id = cloud_id  # Atlassian site/cloud ID
        self.project_key = project_key
        self._issue_type_id: Optional[str] = None

    @property
    def api_url(self) -> str:
        """Get the Jira REST API URL for the connected site."""
        if self.cloud_id:
            return f"{self.API_BASE_URL}/ex/jira/{self.cloud_id}/rest/api/3"
        return ""

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """Generate Jira/Atlassian OAuth authorization URL."""
        params = {
            "audience": "api.atlassian.com",
            "client_id": JIRA_CLIENT_ID,
            "scope": "read:jira-work read:jira-user write:jira-work offline_access",
            "redirect_uri": redirect_uri,
            "state": str(user_id),
            "response_type": "code",
            "prompt": "consent",
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
                json={
                    "grant_type": "authorization_code",
                    "client_id": JIRA_CLIENT_ID,
                    "client_secret": JIRA_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )

            if response.status_code != 200:
                logger.error(f"Jira token exchange failed: {response.text}")
                return {"success": False, "error": response.text}

            data = response.json()

            # Store tokens temporarily to get accessible resources
            self.access_token = data.get("access_token")

            # Get accessible resources (Jira sites)
            sites = await self._get_accessible_resources()

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
                "scope": data.get("scope"),
                "sites": sites,
            }

        except Exception as e:
            logger.error(f"Jira OAuth error: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> Optional[str]:
        """Refresh the Jira access token."""
        if not self.refresh_token:
            return None

        try:
            response = await self.client.post(
                self.OAUTH_TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "client_id": JIRA_CLIENT_ID,
                    "client_secret": JIRA_CLIENT_SECRET,
                    "refresh_token": self.refresh_token,
                },
            )

            if response.status_code != 200:
                logger.error(f"Jira token refresh failed: {response.text}")
                return None

            data = response.json()
            self.access_token = data.get("access_token")
            # Jira returns a new refresh token
            new_refresh = data.get("refresh_token")
            if new_refresh:
                self.refresh_token = new_refresh

            return self.access_token

        except Exception as e:
            logger.error(f"Jira token refresh error: {e}")
            return None

    async def _get_accessible_resources(self) -> List[Dict[str, Any]]:
        """Get list of Jira sites the user has access to."""
        try:
            response = await self.client.get(
                f"{self.API_BASE_URL}/oauth/token/accessible-resources",
            )

            if response.status_code != 200:
                return []

            return response.json()

        except Exception as e:
            logger.error(f"Error getting Jira resources: {e}")
            return []

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_task(self, task: TaskData) -> SyncResult:
        """Create an issue in Jira."""
        if not self.cloud_id or not self.project_key:
            return SyncResult(
                success=False,
                error="No project selected. Please select a Jira project first."
            )

        try:
            # Get Task issue type ID
            issue_type_id = await self._get_task_issue_type()
            if not issue_type_id:
                return SyncResult(
                    success=False,
                    error="Could not find Task issue type in project"
                )

            # Build issue fields
            fields = self._build_issue_fields(task, issue_type_id)

            response = await self.client.post(
                f"{self.api_url}/issue",
                json={"fields": fields},
            )

            if response.status_code not in (200, 201):
                logger.error(f"Jira create issue failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            data = response.json()

            # Build the issue URL
            # Get base URL from accessible resources
            issue_url = f"https://your-domain.atlassian.net/browse/{data.get('key')}"

            return SyncResult(
                success=True,
                external_id=data.get("id"),
                external_url=issue_url,
                metadata={
                    "jira_id": data.get("id"),
                    "jira_key": data.get("key"),
                }
            )

        except Exception as e:
            logger.error(f"Error creating Jira issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """Update an existing Jira issue."""
        try:
            # Get issue type for the existing issue
            existing_issue = await self.get_task(external_id)
            if not existing_issue:
                return SyncResult(success=False, error="Issue not found")

            issue_type_id = existing_issue.get("fields", {}).get("issuetype", {}).get("id")

            fields = self._build_issue_fields(task, issue_type_id, is_update=True)

            response = await self.client.put(
                f"{self.api_url}/issue/{external_id}",
                json={"fields": fields},
            )

            if response.status_code not in (200, 204):
                logger.error(f"Jira update issue failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            return SyncResult(
                success=True,
                external_id=external_id,
            )

        except Exception as e:
            logger.error(f"Error updating Jira issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def delete_task(self, external_id: str) -> SyncResult:
        """Delete a Jira issue."""
        try:
            response = await self.client.delete(
                f"{self.api_url}/issue/{external_id}",
            )

            if response.status_code not in (200, 204):
                logger.error(f"Jira delete issue failed: {response.text}")
                return SyncResult(success=False, error=response.text)

            return SyncResult(success=True, external_id=external_id)

        except Exception as e:
            logger.error(f"Error deleting Jira issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """Get the current status from Jira."""
        task_data = await self.get_task(external_id)
        if not task_data:
            return None

        status = task_data.get("fields", {}).get("status", {})
        status_category = status.get("statusCategory", {}).get("key", "")

        return self.STATUS_CATEGORY_MAPPING.get(status_category, TaskStatus.PENDING)

    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get issue details from Jira."""
        if not self.cloud_id:
            return None

        try:
            response = await self.client.get(
                f"{self.api_url}/issue/{external_id}",
                params={
                    "fields": "summary,description,status,priority,duedate,assignee,labels,issuetype"
                },
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"Jira get issue failed: {response.text}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Error getting Jira issue: {e}")
            return None

    # =========================================================================
    # WORKSPACE/PROJECT METHODS
    # =========================================================================

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List accessible Jira sites."""
        sites = await self._get_accessible_resources()
        return [
            {
                "id": site.get("id"),
                "name": site.get("name"),
                "url": site.get("url"),
                "scopes": site.get("scopes", []),
            }
            for site in sites
        ]

    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List Jira projects."""
        cloud = workspace_id or self.cloud_id
        if not cloud:
            return []

        # Temporarily set cloud_id for API URL
        original_cloud_id = self.cloud_id
        self.cloud_id = cloud

        try:
            response = await self.client.get(
                f"{self.api_url}/project/search",
                params={
                    "maxResults": 100,
                    "orderBy": "name",
                },
            )

            if response.status_code != 200:
                logger.error(f"Jira list projects failed: {response.text}")
                return []

            data = response.json()
            projects = data.get("values", [])

            return [
                {
                    "id": proj.get("id"),
                    "key": proj.get("key"),
                    "name": proj.get("name"),
                    "style": proj.get("style"),
                }
                for proj in projects
            ]

        except Exception as e:
            logger.error(f"Error listing Jira projects: {e}")
            return []

        finally:
            self.cloud_id = original_cloud_id

    async def list_issue_types(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List issue types available in a project."""
        project = project_key or self.project_key
        if not self.cloud_id or not project:
            return []

        try:
            response = await self.client.get(
                f"{self.api_url}/issue/createmeta",
                params={
                    "projectKeys": project,
                    "expand": "projects.issuetypes",
                },
            )

            if response.status_code != 200:
                logger.error(f"Jira list issue types failed: {response.text}")
                return []

            data = response.json()
            projects = data.get("projects", [])
            if not projects:
                return []

            issue_types = projects[0].get("issuetypes", [])
            return [
                {
                    "id": it.get("id"),
                    "name": it.get("name"),
                    "description": it.get("description"),
                    "subtask": it.get("subtask", False),
                }
                for it in issue_types
            ]

        except Exception as e:
            logger.error(f"Error listing Jira issue types: {e}")
            return []

    async def list_statuses(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List statuses available in a project."""
        project = project_key or self.project_key
        if not self.cloud_id or not project:
            return []

        try:
            response = await self.client.get(
                f"{self.api_url}/project/{project}/statuses",
            )

            if response.status_code != 200:
                return []

            data = response.json()
            # Flatten statuses from all issue types
            all_statuses = {}
            for issue_type in data:
                for status in issue_type.get("statuses", []):
                    all_statuses[status.get("id")] = {
                        "id": status.get("id"),
                        "name": status.get("name"),
                        "category": status.get("statusCategory", {}).get("key"),
                    }

            return list(all_statuses.values())

        except Exception as e:
            logger.error(f"Error listing Jira statuses: {e}")
            return []

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_task_issue_type(self) -> Optional[str]:
        """Get the ID of the Task issue type."""
        if self._issue_type_id:
            return self._issue_type_id

        issue_types = await self.list_issue_types()
        for it in issue_types:
            if it.get("name", "").lower() == "task" and not it.get("subtask"):
                self._issue_type_id = it.get("id")
                return self._issue_type_id

        # Fallback to first non-subtask type
        for it in issue_types:
            if not it.get("subtask"):
                self._issue_type_id = it.get("id")
                return self._issue_type_id

        return None

    def _build_issue_fields(
        self,
        task: TaskData,
        issue_type_id: str,
        is_update: bool = False,
    ) -> Dict[str, Any]:
        """Build Jira issue fields from TaskData."""
        fields = {
            "summary": task.title,
            "description": self._build_description(task),
        }

        # Only set these on create
        if not is_update:
            fields["project"] = {"key": self.project_key}
            fields["issuetype"] = {"id": issue_type_id}

        # Priority (use ID)
        priority_id = self.PRIORITY_MAPPING.get(task.priority, "3")
        fields["priority"] = {"id": priority_id}

        # Due date
        if task.due_date:
            fields["duedate"] = task.due_date.strftime("%Y-%m-%d")

        # Labels
        fields["labels"] = ["ReadIn-AI", "action-item"]
        if task.meeting_title:
            # Sanitize meeting title for label
            label = task.meeting_title.replace(" ", "-")[:50]
            label = "".join(c for c in label if c.isalnum() or c == "-")
            if label:
                fields["labels"].append(label)

        return fields

    def _build_description(self, task: TaskData) -> Dict[str, Any]:
        """Build Atlassian Document Format (ADF) description."""
        content = []

        # Main description
        if task.description:
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": task.description}]
            })

        # Horizontal rule
        content.append({"type": "rule"})

        # Metadata panel
        panel_content = [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"ReadIn AI Action Item #{task.id}", "marks": [{"type": "strong"}]}
                ]
            }
        ]

        if task.meeting_title:
            panel_content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Meeting: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": task.meeting_title}
                ]
            })

        if task.assignee:
            panel_content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Assigned to: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": task.assignee}
                ]
            })

        content.append({
            "type": "panel",
            "attrs": {"panelType": "info"},
            "content": panel_content
        })

        return {
            "type": "doc",
            "version": 1,
            "content": content
        }

    async def transition_issue(
        self,
        issue_id: str,
        status: TaskStatus,
    ) -> bool:
        """Transition an issue to a different status."""
        if not self.cloud_id:
            return False

        try:
            # Get available transitions
            response = await self.client.get(
                f"{self.api_url}/issue/{issue_id}/transitions",
            )

            if response.status_code != 200:
                return False

            transitions = response.json().get("transitions", [])

            # Find matching transition
            target_category = {
                TaskStatus.PENDING: "new",
                TaskStatus.IN_PROGRESS: "indeterminate",
                TaskStatus.COMPLETED: "done",
                TaskStatus.CANCELLED: "done",
            }.get(status)

            for trans in transitions:
                trans_category = trans.get("to", {}).get("statusCategory", {}).get("key")
                if trans_category == target_category:
                    # Perform transition
                    response = await self.client.post(
                        f"{self.api_url}/issue/{issue_id}/transitions",
                        json={"transition": {"id": trans.get("id")}},
                    )
                    return response.status_code in (200, 204)

            return False

        except Exception as e:
            logger.error(f"Error transitioning Jira issue: {e}")
            return False

    def map_priority_to_external(self, priority: TaskPriority) -> str:
        """Map internal priority to Jira priority ID."""
        return self.PRIORITY_MAPPING.get(priority, "3")

    def map_priority_from_external(self, external_priority: str) -> TaskPriority:
        """Map Jira priority name to internal priority."""
        return self.REVERSE_PRIORITY_MAPPING.get(external_priority, TaskPriority.MEDIUM)
