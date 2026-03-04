"""
Monday.com Integration for ReadIn AI.

Syncs action items to Monday.com as items within boards.

Monday.com API Documentation: https://developer.monday.com/api-reference/

Features:
- OAuth 2.0 authentication
- Create items in boards using GraphQL API
- Update items
- List boards and groups
- Sync task status bidirectionally
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

logger = logging.getLogger("monday")

# Configuration from environment
MONDAY_CLIENT_ID = os.getenv("MONDAY_CLIENT_ID", "")
MONDAY_CLIENT_SECRET = os.getenv("MONDAY_CLIENT_SECRET", "")
MONDAY_REDIRECT_URI = os.getenv("MONDAY_REDIRECT_URI", "")


def is_monday_configured() -> bool:
    """Check if Monday.com integration is configured."""
    return bool(MONDAY_CLIENT_ID and MONDAY_CLIENT_SECRET)


class MondayIntegration(ProjectManagementIntegration):
    """
    Monday.com integration for syncing action items.

    Creates items in Monday.com boards with:
    - Name/Title
    - Status column
    - Priority column
    - Due date column
    - Person column (assignee)
    - Text column (description)

    Uses Monday.com's GraphQL API for all operations.
    """

    PROVIDER_NAME = "monday"
    DISPLAY_NAME = "Monday.com"
    OAUTH_AUTHORIZE_URL = "https://auth.monday.com/oauth2/authorize"
    OAUTH_TOKEN_URL = "https://auth.monday.com/oauth2/token"
    API_BASE_URL = "https://api.monday.com/v2"

    # Status mapping - Monday.com uses customizable status labels
    # These are common defaults, actual values depend on board configuration
    STATUS_MAPPING = {
        TaskStatus.PENDING: "Working on it",
        TaskStatus.IN_PROGRESS: "Working on it",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.CANCELLED: "Stuck",
    }

    REVERSE_STATUS_MAPPING = {
        "Working on it": TaskStatus.IN_PROGRESS,
        "Done": TaskStatus.COMPLETED,
        "Stuck": TaskStatus.CANCELLED,
        "Not Started": TaskStatus.PENDING,
        "": TaskStatus.PENDING,
    }

    # Priority mapping - Monday.com priority column values
    PRIORITY_MAPPING = {
        TaskPriority.LOW: "Low",
        TaskPriority.MEDIUM: "Medium",
        TaskPriority.HIGH: "High",
        TaskPriority.URGENT: "Critical",
    }

    REVERSE_PRIORITY_MAPPING = {
        "Low": TaskPriority.LOW,
        "Medium": TaskPriority.MEDIUM,
        "High": TaskPriority.HIGH,
        "Critical": TaskPriority.URGENT,
    }

    def __init__(
        self,
        db,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        board_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ):
        super().__init__(db, access_token, refresh_token)
        self.board_id = board_id
        self.group_id = group_id
        self._column_ids: Optional[Dict[str, str]] = None

    def _get_default_headers(self) -> Dict[str, str]:
        """Get Monday.com-specific headers."""
        headers = {
            "Content-Type": "application/json",
            "API-Version": "2024-01",
        }
        if self.access_token:
            headers["Authorization"] = self.access_token
        return headers

    # =========================================================================
    # GRAPHQL HELPER
    # =========================================================================

    async def _graphql_request(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL request to Monday.com API.

        Args:
            query: GraphQL query string
            variables: Optional variables for the query

        Returns:
            Response data dictionary
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.client.post(
            self.API_BASE_URL,
            json=payload,
        )

        if response.status_code != 200:
            logger.error(f"Monday.com GraphQL error: {response.text}")
            raise Exception(f"GraphQL request failed: {response.text}")

        result = response.json()

        if "errors" in result:
            error_messages = [e.get("message", "Unknown error") for e in result["errors"]]
            logger.error(f"Monday.com GraphQL errors: {error_messages}")
            raise Exception(f"GraphQL errors: {'; '.join(error_messages)}")

        return result.get("data", {})

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """Generate Monday.com OAuth authorization URL."""
        params = {
            "client_id": MONDAY_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "state": str(user_id),
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
                    "client_id": MONDAY_CLIENT_ID,
                    "client_secret": MONDAY_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Monday.com token exchange failed: {response.text}")
                return {"success": False, "error": response.text}

            data = response.json()

            # Get user info using the token
            self.access_token = data.get("access_token")

            user_info = await self._get_current_user()

            return {
                "success": True,
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type"),
                "user_id": user_info.get("id") if user_info else None,
                "user_name": user_info.get("name") if user_info else None,
                "user_email": user_info.get("email") if user_info else None,
                "account_id": user_info.get("account", {}).get("id") if user_info else None,
                "account_name": user_info.get("account", {}).get("name") if user_info else None,
            }

        except Exception as e:
            logger.error(f"Monday.com OAuth error: {e}")
            return {"success": False, "error": str(e)}

    async def _get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        query = """
        query {
            me {
                id
                name
                email
                account {
                    id
                    name
                }
            }
        }
        """
        try:
            data = await self._graphql_request(query)
            return data.get("me")
        except Exception as e:
            logger.error(f"Error getting Monday.com user: {e}")
            return None

    async def refresh_access_token(self) -> Optional[str]:
        """
        Monday.com tokens don't expire with the standard OAuth flow.
        Return the existing access token.
        """
        return self.access_token

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    async def create_task(self, task: TaskData) -> SyncResult:
        """Create an item in Monday.com board."""
        if not self.board_id:
            return SyncResult(
                success=False,
                error="No board selected. Please select a Monday.com board first."
            )

        try:
            # Build column values
            column_values = await self._build_column_values(task)

            # GraphQL mutation to create item
            query = """
            mutation CreateItem($boardId: ID!, $groupId: String, $itemName: String!, $columnValues: JSON) {
                create_item(
                    board_id: $boardId
                    group_id: $groupId
                    item_name: $itemName
                    column_values: $columnValues
                ) {
                    id
                    name
                }
            }
            """

            variables = {
                "boardId": self.board_id,
                "itemName": task.title,
                "columnValues": column_values,
            }

            if self.group_id:
                variables["groupId"] = self.group_id

            data = await self._graphql_request(query, variables)
            item = data.get("create_item", {})

            if not item.get("id"):
                return SyncResult(success=False, error="Failed to create item")

            # Get item URL
            item_url = f"https://view.monday.com/board/{self.board_id}/pulses/{item['id']}"

            return SyncResult(
                success=True,
                external_id=str(item.get("id")),
                external_url=item_url,
                metadata={
                    "monday_item_id": item.get("id"),
                    "board_id": self.board_id,
                }
            )

        except Exception as e:
            logger.error(f"Error creating Monday.com item: {e}")
            return SyncResult(success=False, error=str(e))

    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """Update an existing Monday.com item."""
        try:
            # Build column values
            column_values = await self._build_column_values(task)

            # GraphQL mutation to update item
            query = """
            mutation UpdateItem($itemId: ID!, $boardId: ID!, $columnValues: JSON!) {
                change_multiple_column_values(
                    item_id: $itemId
                    board_id: $boardId
                    column_values: $columnValues
                ) {
                    id
                    name
                }
            }
            """

            variables = {
                "itemId": external_id,
                "boardId": self.board_id,
                "columnValues": column_values,
            }

            data = await self._graphql_request(query, variables)
            item = data.get("change_multiple_column_values", {})

            item_url = f"https://view.monday.com/board/{self.board_id}/pulses/{external_id}"

            return SyncResult(
                success=True,
                external_id=str(item.get("id", external_id)),
                external_url=item_url,
            )

        except Exception as e:
            logger.error(f"Error updating Monday.com item: {e}")
            return SyncResult(success=False, error=str(e))

    async def delete_task(self, external_id: str) -> SyncResult:
        """Archive (delete) a Monday.com item."""
        try:
            query = """
            mutation ArchiveItem($itemId: ID!) {
                archive_item(item_id: $itemId) {
                    id
                }
            }
            """

            variables = {"itemId": external_id}

            await self._graphql_request(query, variables)

            return SyncResult(success=True, external_id=external_id)

        except Exception as e:
            logger.error(f"Error archiving Monday.com item: {e}")
            return SyncResult(success=False, error=str(e))

    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """Get the current status from Monday.com."""
        task_data = await self.get_task(external_id)
        if not task_data:
            return None

        # Find status column value
        column_values = task_data.get("column_values", [])
        for col in column_values:
            if col.get("type") == "status":
                status_text = col.get("text", "")
                return self.REVERSE_STATUS_MAPPING.get(status_text, TaskStatus.PENDING)

        return TaskStatus.PENDING

    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get item details from Monday.com."""
        try:
            query = """
            query GetItem($itemId: [ID!]) {
                items(ids: $itemId) {
                    id
                    name
                    state
                    column_values {
                        id
                        type
                        text
                        value
                    }
                }
            }
            """

            variables = {"itemId": [external_id]}

            data = await self._graphql_request(query, variables)
            items = data.get("items", [])

            if items:
                return items[0]

            return None

        except Exception as e:
            logger.error(f"Error getting Monday.com item: {e}")
            return None

    # =========================================================================
    # WORKSPACE/BOARD METHODS
    # =========================================================================

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List Monday.com workspaces."""
        try:
            query = """
            query {
                workspaces {
                    id
                    name
                    kind
                    description
                }
            }
            """

            data = await self._graphql_request(query)
            workspaces = data.get("workspaces", [])

            return [
                {
                    "id": ws.get("id"),
                    "name": ws.get("name"),
                    "kind": ws.get("kind"),
                    "description": ws.get("description"),
                }
                for ws in workspaces
            ]

        except Exception as e:
            logger.error(f"Error listing Monday.com workspaces: {e}")
            return []

    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List boards in Monday.com.

        Args:
            workspace_id: Optional workspace filter

        Returns:
            List of boards
        """
        try:
            if workspace_id:
                query = """
                query GetBoards($workspaceId: [ID!]) {
                    boards(workspace_ids: $workspaceId, limit: 100) {
                        id
                        name
                        description
                        state
                        board_kind
                        workspace_id
                    }
                }
                """
                variables = {"workspaceId": [workspace_id]}
            else:
                query = """
                query {
                    boards(limit: 100) {
                        id
                        name
                        description
                        state
                        board_kind
                        workspace_id
                    }
                }
                """
                variables = None

            data = await self._graphql_request(query, variables)
            boards = data.get("boards", [])

            return [
                {
                    "id": board.get("id"),
                    "name": board.get("name"),
                    "description": board.get("description"),
                    "state": board.get("state"),
                    "kind": board.get("board_kind"),
                    "workspace_id": board.get("workspace_id"),
                    "url": f"https://view.monday.com/board/{board.get('id')}",
                }
                for board in boards
                if board.get("state") == "active"
            ]

        except Exception as e:
            logger.error(f"Error listing Monday.com boards: {e}")
            return []

    async def list_groups(self, board_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List groups within a board."""
        board = board_id or self.board_id
        if not board:
            return []

        try:
            query = """
            query GetGroups($boardId: [ID!]) {
                boards(ids: $boardId) {
                    groups {
                        id
                        title
                        color
                        position
                    }
                }
            }
            """

            variables = {"boardId": [board]}

            data = await self._graphql_request(query, variables)
            boards = data.get("boards", [])

            if boards:
                groups = boards[0].get("groups", [])
                return [
                    {
                        "id": group.get("id"),
                        "name": group.get("title"),
                        "color": group.get("color"),
                        "position": group.get("position"),
                    }
                    for group in groups
                ]

            return []

        except Exception as e:
            logger.error(f"Error listing Monday.com groups: {e}")
            return []

    async def get_board_columns(self, board_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column definitions for a board."""
        board = board_id or self.board_id
        if not board:
            return []

        try:
            query = """
            query GetColumns($boardId: [ID!]) {
                boards(ids: $boardId) {
                    columns {
                        id
                        title
                        type
                        settings_str
                    }
                }
            }
            """

            variables = {"boardId": [board]}

            data = await self._graphql_request(query, variables)
            boards = data.get("boards", [])

            if boards:
                return boards[0].get("columns", [])

            return []

        except Exception as e:
            logger.error(f"Error getting Monday.com columns: {e}")
            return []

    async def _get_column_ids(self) -> Dict[str, str]:
        """
        Get column ID mappings for the current board.

        Maps common column types to their IDs:
        - status: Status column
        - date: Due date column
        - text: Description column
        - people: Assignee column
        - priority: Priority column (often a status type)
        """
        if self._column_ids is not None:
            return self._column_ids

        columns = await self.get_board_columns()

        self._column_ids = {}

        # Map columns by type and common names
        for col in columns:
            col_type = col.get("type", "")
            col_title = col.get("title", "").lower()
            col_id = col.get("id")

            # Status column
            if col_type == "status" and "priority" not in col_title:
                if "status" not in self._column_ids:
                    self._column_ids["status"] = col_id

            # Priority column (often a status column with "priority" in name)
            if col_type == "status" and "priority" in col_title:
                self._column_ids["priority"] = col_id

            # Date column
            if col_type == "date":
                if "due" in col_title or "date" not in self._column_ids:
                    self._column_ids["date"] = col_id

            # Text column for description
            if col_type == "text" or col_type == "long_text":
                if "description" in col_title or "notes" in col_title:
                    self._column_ids["text"] = col_id
                elif "text" not in self._column_ids:
                    self._column_ids["text"] = col_id

            # People column for assignee
            if col_type == "people":
                self._column_ids["people"] = col_id

        return self._column_ids

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _build_column_values(self, task: TaskData) -> str:
        """
        Build Monday.com column values JSON from TaskData.

        Returns a JSON string of column values.
        """
        import json

        column_ids = await self._get_column_ids()
        column_values = {}

        # Status
        if "status" in column_ids:
            status_label = self.STATUS_MAPPING.get(task.status, "Working on it")
            column_values[column_ids["status"]] = {"label": status_label}

        # Priority
        if "priority" in column_ids:
            priority_label = self.PRIORITY_MAPPING.get(task.priority, "Medium")
            column_values[column_ids["priority"]] = {"label": priority_label}

        # Due date
        if "date" in column_ids and task.due_date:
            column_values[column_ids["date"]] = {
                "date": task.due_date.strftime("%Y-%m-%d")
            }

        # Description/Notes
        if "text" in column_ids:
            description = self._build_description(task)
            column_values[column_ids["text"]] = description

        return json.dumps(column_values)

    def _build_description(self, task: TaskData) -> str:
        """Build the description/notes field."""
        parts = []

        if task.description:
            parts.append(task.description)

        parts.append("")
        parts.append("---")
        parts.append(f"ReadIn AI Action Item #{task.id}")

        if task.meeting_title:
            parts.append(f"Meeting: {task.meeting_title}")

        if task.assignee:
            parts.append(f"Assigned to: {task.assignee}")

        return "\n".join(parts)

    def map_status_to_external(self, status: TaskStatus) -> str:
        """Map internal status to Monday.com status label."""
        return self.STATUS_MAPPING.get(status, "Working on it")

    def map_status_from_external(self, external_status: str) -> TaskStatus:
        """Map Monday.com status to internal status."""
        return self.REVERSE_STATUS_MAPPING.get(external_status, TaskStatus.PENDING)

    def map_priority_to_external(self, priority: TaskPriority) -> str:
        """Map internal priority to Monday.com priority label."""
        return self.PRIORITY_MAPPING.get(priority, "Medium")

    def map_priority_from_external(self, external_priority: str) -> TaskPriority:
        """Map Monday.com priority to internal priority."""
        return self.REVERSE_PRIORITY_MAPPING.get(external_priority, TaskPriority.MEDIUM)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a Monday.com user by email for assignee mapping."""
        try:
            query = """
            query {
                users {
                    id
                    name
                    email
                }
            }
            """

            data = await self._graphql_request(query)
            users = data.get("users", [])

            for user in users:
                if user.get("email", "").lower() == email.lower():
                    return user

            return None

        except Exception as e:
            logger.error(f"Error finding Monday.com user: {e}")
            return None

    async def add_update_to_item(self, item_id: str, update_text: str) -> bool:
        """Add an update/comment to an item."""
        try:
            query = """
            mutation AddUpdate($itemId: ID!, $body: String!) {
                create_update(item_id: $itemId, body: $body) {
                    id
                }
            }
            """

            variables = {
                "itemId": item_id,
                "body": update_text,
            }

            await self._graphql_request(query, variables)
            return True

        except Exception as e:
            logger.error(f"Error adding update to Monday.com item: {e}")
            return False
