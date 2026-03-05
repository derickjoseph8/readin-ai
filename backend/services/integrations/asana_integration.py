"""
Asana Integration - Sync action items with Asana tasks.
"""

import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class AsanaIntegration:
    """Asana API integration for syncing action items."""

    BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request to Asana."""
        url = f"{self.BASE_URL}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json={"data": data} if data else None
            )

            if response.status_code >= 400:
                logger.error(f"Asana API error: {response.status_code} - {response.text}")
                raise Exception(f"Asana API error: {response.status_code}")

            return response.json().get("data", {})

    async def get_user(self) -> Dict:
        """Get current user info."""
        return await self._request("GET", "users/me")

    async def get_workspaces(self) -> List[Dict]:
        """Get user's Asana workspaces."""
        return await self._request("GET", "workspaces")

    async def get_projects(self, workspace_id: str) -> List[Dict]:
        """Get projects in a workspace."""
        return await self._request("GET", f"workspaces/{workspace_id}/projects")

    async def get_sections(self, project_id: str) -> List[Dict]:
        """Get sections in a project."""
        return await self._request("GET", f"projects/{project_id}/sections")

    async def create_task(
        self,
        project_id: str,
        name: str,
        notes: str = "",
        due_on: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict:
        """
        Create a task in Asana.

        Args:
            project_id: Asana project ID
            name: Task name
            notes: Task description
            due_on: Due date (YYYY-MM-DD)
            assignee: Assignee user ID

        Returns:
            Created task data
        """
        data = {
            "name": name,
            "notes": notes,
            "projects": [project_id]
        }

        if due_on:
            data["due_on"] = due_on
        if assignee:
            data["assignee"] = assignee

        return await self._request("POST", "tasks", data)

    async def update_task(
        self,
        task_id: str,
        completed: Optional[bool] = None,
        name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Update an existing task."""
        data = {}
        if completed is not None:
            data["completed"] = completed
        if name:
            data["name"] = name
        if notes:
            data["notes"] = notes

        return await self._request("PUT", f"tasks/{task_id}", data)

    async def sync_action_item(
        self,
        action_item: Any,
        project_id: str
    ) -> Dict:
        """
        Sync a ReadIn action item to Asana.

        Args:
            action_item: ActionItem model instance
            project_id: Target Asana project

        Returns:
            Created Asana task data
        """
        due_on = None
        if action_item.due_date:
            due_on = action_item.due_date.strftime("%Y-%m-%d")

        notes = f"From ReadIn AI meeting\n\n{action_item.description or ''}"

        task = await self.create_task(
            project_id=project_id,
            name=action_item.title,
            notes=notes,
            due_on=due_on
        )

        logger.info(f"Synced action item {action_item.id} to Asana task {task.get('gid')}")
        return task

    async def sync_all_pending(
        self,
        action_items: List[Any],
        project_id: str
    ) -> List[Dict]:
        """Sync multiple action items."""
        results = []
        for item in action_items:
            if item.status in ["pending", "in_progress"]:
                try:
                    task = await self.sync_action_item(item, project_id)
                    results.append({"item_id": str(item.id), "asana_task": task})
                except Exception as e:
                    logger.error(f"Failed to sync action item {item.id}: {e}")
                    results.append({"item_id": str(item.id), "error": str(e)})
        return results


def get_asana_oauth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Generate Asana OAuth URL."""
    return (
        f"https://app.asana.com/-/oauth_authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state={state}"
    )


async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Dict:
    """Exchange OAuth code for access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://app.asana.com/-/oauth_token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        return response.json()
