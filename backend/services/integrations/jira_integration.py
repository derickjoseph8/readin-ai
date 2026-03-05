"""
Jira Integration - Sync action items with Jira issues.
"""

import logging
from typing import List, Dict, Optional, Any
import httpx
import base64

logger = logging.getLogger(__name__)


class JiraIntegration:
    """Jira API integration for syncing action items."""

    def __init__(self, domain: str, email: str, api_token: str):
        """
        Initialize Jira integration.

        Args:
            domain: Jira domain (e.g., 'company' for company.atlassian.net)
            email: User email for authentication
            api_token: Jira API token
        """
        self.base_url = f"https://{domain}.atlassian.net/rest/api/3"
        self.auth = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {self.auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request to Jira."""
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )

            if response.status_code >= 400:
                logger.error(f"Jira API error: {response.status_code} - {response.text}")
                raise Exception(f"Jira API error: {response.status_code}")

            if response.status_code == 204:
                return {}

            return response.json()

    async def get_projects(self) -> List[Dict]:
        """Get accessible Jira projects."""
        return await self._request("GET", "project")

    async def get_issue_types(self, project_key: str) -> List[Dict]:
        """Get issue types for a project."""
        project = await self._request("GET", f"project/{project_key}")
        return project.get("issueTypes", [])

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> Dict:
        """
        Create a Jira issue.

        Args:
            project_key: Project key (e.g., 'PROJ')
            summary: Issue summary/title
            description: Issue description
            issue_type: Issue type (Task, Story, Bug, etc.)
            priority: Priority name
            assignee: Assignee account ID

        Returns:
            Created issue data
        """
        # Build Atlassian Document Format for description
        adf_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": description}
                    ]
                }
            ]
        }

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": adf_description,
            "issuetype": {"name": issue_type}
        }

        if priority:
            fields["priority"] = {"name": priority}
        if assignee:
            fields["assignee"] = {"accountId": assignee}

        return await self._request("POST", "issue", {"fields": fields})

    async def get_issue(self, issue_key: str) -> Dict:
        """Get issue details."""
        return await self._request("GET", f"issue/{issue_key}")

    async def update_issue(
        self,
        issue_key: str,
        fields: Optional[Dict] = None,
        transition_id: Optional[str] = None
    ) -> Dict:
        """Update an issue."""
        if fields:
            await self._request("PUT", f"issue/{issue_key}", {"fields": fields})

        if transition_id:
            await self._request(
                "POST",
                f"issue/{issue_key}/transitions",
                {"transition": {"id": transition_id}}
            )

        return await self.get_issue(issue_key)

    async def get_transitions(self, issue_key: str) -> List[Dict]:
        """Get available transitions for an issue."""
        result = await self._request("GET", f"issue/{issue_key}/transitions")
        return result.get("transitions", [])

    async def add_comment(self, issue_key: str, comment: str) -> Dict:
        """Add comment to an issue."""
        body = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment}]
                }
            ]
        }
        return await self._request(
            "POST",
            f"issue/{issue_key}/comment",
            {"body": body}
        )

    async def sync_action_item(
        self,
        action_item: Any,
        project_key: str,
        issue_type: str = "Task"
    ) -> Dict:
        """
        Sync a ReadIn action item to Jira.

        Args:
            action_item: ActionItem model instance
            project_key: Target Jira project key
            issue_type: Jira issue type

        Returns:
            Created Jira issue data
        """
        description = f"From ReadIn AI meeting\n\n{action_item.description or ''}"

        if action_item.due_date:
            description += f"\n\nDue: {action_item.due_date.strftime('%Y-%m-%d')}"

        # Map priority
        priority_map = {
            "urgent": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low"
        }
        priority = priority_map.get(action_item.priority, "Medium")

        issue = await self.create_issue(
            project_key=project_key,
            summary=action_item.title,
            description=description,
            issue_type=issue_type,
            priority=priority
        )

        logger.info(f"Synced action item {action_item.id} to Jira issue {issue.get('key')}")
        return issue

    async def sync_all_pending(
        self,
        action_items: List[Any],
        project_key: str
    ) -> List[Dict]:
        """Sync multiple action items."""
        results = []
        for item in action_items:
            if item.status in ["pending", "in_progress"]:
                try:
                    issue = await self.sync_action_item(item, project_key)
                    results.append({"item_id": str(item.id), "jira_issue": issue})
                except Exception as e:
                    logger.error(f"Failed to sync action item {item.id}: {e}")
                    results.append({"item_id": str(item.id), "error": str(e)})
        return results
