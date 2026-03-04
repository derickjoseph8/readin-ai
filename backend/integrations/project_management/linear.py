"""
Linear Integration for ReadIn AI.

Syncs action items to Linear as issues.

Linear API Documentation: https://developers.linear.app/docs

Features:
- OAuth 2.0 authentication
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

logger = logging.getLogger("linear")

# Configuration from environment
LINEAR_CLIENT_ID = os.getenv("LINEAR_CLIENT_ID", "")
LINEAR_CLIENT_SECRET = os.getenv("LINEAR_CLIENT_SECRET", "")
LINEAR_REDIRECT_URI = os.getenv("LINEAR_REDIRECT_URI", "")


def is_linear_configured() -> bool:
    """Check if Linear integration is configured."""
    return bool(LINEAR_CLIENT_ID and LINEAR_CLIENT_SECRET)


class LinearIntegration(ProjectManagementIntegration):
    """
    Linear integration for syncing action items.

    Creates issues in Linear with:
    - Title
    - Description (markdown)
    - State (workflow state)
    - Priority (1-4)
    - Due Date
    - Assignee
    - Labels
    """

    PROVIDER_NAME = "linear"
    DISPLAY_NAME = "Linear"
    OAUTH_AUTHORIZE_URL = "https://linear.app/oauth/authorize"
    OAUTH_TOKEN_URL = "https://api.linear.app/oauth/token"
    API_BASE_URL = "https://api.linear.app/graphql"

    # Linear priorities: 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
    PRIORITY_MAPPING = {
        TaskPriority.URGENT: 1,
        TaskPriority.HIGH: 2,
        TaskPriority.MEDIUM: 3,
        TaskPriority.LOW: 4,
    }

    REVERSE_PRIORITY_MAPPING = {
        0: TaskPriority.MEDIUM,  # None -> Medium
        1: TaskPriority.URGENT,
        2: TaskPriority.HIGH,
        3: TaskPriority.MEDIUM,
        4: TaskPriority.LOW,
    }

    # Linear uses workflow states - these are common names
    STATUS_STATE_TYPES = {
        TaskStatus.PENDING: "unstarted",
        TaskStatus.IN_PROGRESS: "started",
        TaskStatus.COMPLETED: "completed",
        TaskStatus.CANCELLED: "canceled",
    }

    def __init__(
        self,
        db,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        super().__init__(db, access_token, refresh_token)
        self.team_id = team_id
        self._workflow_states: Dict[str, str] = {}

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """Generate Linear OAuth authorization URL."""
        params = {
            "client_id": LINEAR_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": str(user_id),
            "scope": "read,write,issues:create",
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
                data={
                    "grant_type": "authorization_code",
                    "client_id": LINEAR_CLIENT_ID,
                    "client_secret": LINEAR_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Linear token exchange failed: {response.text}")
                return {"success": False, "error": response.text}

            data = response.json()

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type"),
                "expires_in": data.get("expires_in"),
                "scope": data.get("scope"),
            }

        except Exception as e:
            logger.error(f"Linear OAuth error: {e}")
            return {"success": False, "error": str(e)}

    async def refresh_access_token(self) -> Optional[str]:
        """
        Linear tokens don't expire (they're API keys after OAuth).
        Return the existing access token.
        """
        return self.access_token

    # =========================================================================
    # GRAPHQL HELPER
    # =========================================================================

    async def _graphql(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against Linear's API."""
        try:
            response = await self.client.post(
                self.API_BASE_URL,
                json={
                    "query": query,
                    "variables": variables or {},
                },
            )

            if response.status_code != 200:
                logger.error(f"Linear GraphQL error: {response.text}")
                return {"errors": [{"message": response.text}]}

            return response.json()

        except Exception as e:
            logger.error(f"Linear GraphQL request error: {e}")
            return {"errors": [{"message": str(e)}]}

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_task(self, task: TaskData) -> SyncResult:
        """Create an issue in Linear."""
        if not self.team_id:
            return SyncResult(
                success=False,
                error="No team selected. Please select a Linear team first."
            )

        try:
            # Get workflow state for initial status
            state_id = await self._get_workflow_state(task.status)

            mutation = """
            mutation IssueCreate($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                        createdAt
                    }
                }
            }
            """

            variables = {
                "input": {
                    "teamId": self.team_id,
                    "title": task.title,
                    "description": self._build_description(task),
                    "priority": self.PRIORITY_MAPPING.get(task.priority, 3),
                }
            }

            if state_id:
                variables["input"]["stateId"] = state_id

            if task.due_date:
                variables["input"]["dueDate"] = task.due_date.strftime("%Y-%m-%d")

            result = await self._graphql(mutation, variables)

            if "errors" in result:
                return SyncResult(
                    success=False,
                    error=str(result["errors"])
                )

            issue_data = result.get("data", {}).get("issueCreate", {})
            if not issue_data.get("success"):
                return SyncResult(success=False, error="Issue creation failed")

            issue = issue_data.get("issue", {})

            return SyncResult(
                success=True,
                external_id=issue.get("id"),
                external_url=issue.get("url"),
                metadata={
                    "linear_id": issue.get("id"),
                    "identifier": issue.get("identifier"),
                    "created_at": issue.get("createdAt"),
                }
            )

        except Exception as e:
            logger.error(f"Error creating Linear issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """Update an existing Linear issue."""
        try:
            state_id = await self._get_workflow_state(task.status)

            mutation = """
            mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                    }
                }
            }
            """

            variables = {
                "id": external_id,
                "input": {
                    "title": task.title,
                    "description": self._build_description(task),
                    "priority": self.PRIORITY_MAPPING.get(task.priority, 3),
                }
            }

            if state_id:
                variables["input"]["stateId"] = state_id

            if task.due_date:
                variables["input"]["dueDate"] = task.due_date.strftime("%Y-%m-%d")
            else:
                variables["input"]["dueDate"] = None

            result = await self._graphql(mutation, variables)

            if "errors" in result:
                return SyncResult(success=False, error=str(result["errors"]))

            issue_data = result.get("data", {}).get("issueUpdate", {})
            if not issue_data.get("success"):
                return SyncResult(success=False, error="Issue update failed")

            issue = issue_data.get("issue", {})

            return SyncResult(
                success=True,
                external_id=issue.get("id"),
                external_url=issue.get("url"),
            )

        except Exception as e:
            logger.error(f"Error updating Linear issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def delete_task(self, external_id: str) -> SyncResult:
        """Archive a Linear issue."""
        try:
            mutation = """
            mutation IssueArchive($id: String!) {
                issueArchive(id: $id) {
                    success
                }
            }
            """

            result = await self._graphql(mutation, {"id": external_id})

            if "errors" in result:
                return SyncResult(success=False, error=str(result["errors"]))

            archive_data = result.get("data", {}).get("issueArchive", {})
            if not archive_data.get("success"):
                return SyncResult(success=False, error="Issue archive failed")

            return SyncResult(success=True, external_id=external_id)

        except Exception as e:
            logger.error(f"Error archiving Linear issue: {e}")
            return SyncResult(success=False, error=str(e))

    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """Get the current status from Linear."""
        task_data = await self.get_task(external_id)
        if not task_data:
            return None

        state = task_data.get("state", {})
        state_type = state.get("type", "")

        # Map state type to TaskStatus
        for ts, st in self.STATUS_STATE_TYPES.items():
            if state_type == st:
                return ts

        return TaskStatus.PENDING

    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get issue details from Linear."""
        try:
            query = """
            query Issue($id: String!) {
                issue(id: $id) {
                    id
                    identifier
                    title
                    description
                    priority
                    dueDate
                    url
                    state {
                        id
                        name
                        type
                    }
                    assignee {
                        id
                        name
                        email
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                }
            }
            """

            result = await self._graphql(query, {"id": external_id})

            if "errors" in result:
                return None

            return result.get("data", {}).get("issue")

        except Exception as e:
            logger.error(f"Error getting Linear issue: {e}")
            return None

    # =========================================================================
    # WORKSPACE/TEAM METHODS
    # =========================================================================

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List Linear organizations (workspaces)."""
        try:
            query = """
            query {
                organization {
                    id
                    name
                    urlKey
                }
            }
            """

            result = await self._graphql(query)

            if "errors" in result:
                return []

            org = result.get("data", {}).get("organization")
            if org:
                return [{
                    "id": org.get("id"),
                    "name": org.get("name"),
                    "url_key": org.get("urlKey"),
                }]

            return []

        except Exception as e:
            logger.error(f"Error listing Linear workspaces: {e}")
            return []

    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List Linear teams (projects)."""
        try:
            query = """
            query {
                teams {
                    nodes {
                        id
                        name
                        key
                        description
                    }
                }
            }
            """

            result = await self._graphql(query)

            if "errors" in result:
                return []

            teams = result.get("data", {}).get("teams", {}).get("nodes", [])
            return [
                {
                    "id": team.get("id"),
                    "name": team.get("name"),
                    "key": team.get("key"),
                    "description": team.get("description"),
                }
                for team in teams
            ]

        except Exception as e:
            logger.error(f"Error listing Linear teams: {e}")
            return []

    async def list_workflow_states(
        self,
        team_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List workflow states for a team."""
        team = team_id or self.team_id
        if not team:
            return []

        try:
            query = """
            query TeamStates($teamId: String!) {
                team(id: $teamId) {
                    states {
                        nodes {
                            id
                            name
                            type
                            color
                            position
                        }
                    }
                }
            }
            """

            result = await self._graphql(query, {"teamId": team})

            if "errors" in result:
                return []

            states = result.get("data", {}).get("team", {}).get("states", {}).get("nodes", [])
            return [
                {
                    "id": state.get("id"),
                    "name": state.get("name"),
                    "type": state.get("type"),
                    "color": state.get("color"),
                }
                for state in states
            ]

        except Exception as e:
            logger.error(f"Error listing Linear workflow states: {e}")
            return []

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _get_workflow_state(self, status: TaskStatus) -> Optional[str]:
        """Get the Linear workflow state ID for a status."""
        if not self.team_id:
            return None

        # Cache workflow states
        if not self._workflow_states:
            states = await self.list_workflow_states()
            self._workflow_states = {
                state.get("type"): state.get("id")
                for state in states
            }

        state_type = self.STATUS_STATE_TYPES.get(status)
        return self._workflow_states.get(state_type)

    def _build_description(self, task: TaskData) -> str:
        """Build markdown description for Linear issue."""
        parts = []

        if task.description:
            parts.append(task.description)
            parts.append("")

        parts.append("---")
        parts.append(f"*ReadIn AI Action Item #{task.id}*")

        if task.meeting_title:
            parts.append(f"**Meeting:** {task.meeting_title}")

        if task.assignee:
            parts.append(f"**Assigned to:** {task.assignee}")

        return "\n".join(parts)

    def map_priority_to_external(self, priority: TaskPriority) -> int:
        """Map internal priority to Linear priority (1-4)."""
        return self.PRIORITY_MAPPING.get(priority, 3)

    def map_priority_from_external(self, external_priority: int) -> TaskPriority:
        """Map Linear priority to internal priority."""
        return self.REVERSE_PRIORITY_MAPPING.get(external_priority, TaskPriority.MEDIUM)
