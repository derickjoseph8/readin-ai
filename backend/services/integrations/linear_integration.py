"""
Linear Integration - Sync action items with Linear issues.
"""

import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class LinearIntegration:
    """Linear GraphQL API integration for syncing action items."""

    GRAPHQL_URL = "https://api.linear.app/graphql"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }

    async def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute GraphQL query."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GRAPHQL_URL,
                headers=self.headers,
                json={"query": query, "variables": variables or {}}
            )

            if response.status_code >= 400:
                logger.error(f"Linear API error: {response.status_code} - {response.text}")
                raise Exception(f"Linear API error: {response.status_code}")

            result = response.json()
            if "errors" in result:
                logger.error(f"Linear GraphQL errors: {result['errors']}")
                raise Exception(f"Linear GraphQL error: {result['errors']}")

            return result.get("data", {})

    async def get_viewer(self) -> Dict:
        """Get current user info."""
        query = """
        query {
            viewer {
                id
                name
                email
            }
        }
        """
        result = await self._graphql(query)
        return result.get("viewer", {})

    async def get_teams(self) -> List[Dict]:
        """Get user's teams."""
        query = """
        query {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """
        result = await self._graphql(query)
        return result.get("teams", {}).get("nodes", [])

    async def get_projects(self, team_id: str) -> List[Dict]:
        """Get projects for a team."""
        query = """
        query($teamId: String!) {
            team(id: $teamId) {
                projects {
                    nodes {
                        id
                        name
                        state
                    }
                }
            }
        }
        """
        result = await self._graphql(query, {"teamId": team_id})
        return result.get("team", {}).get("projects", {}).get("nodes", [])

    async def get_workflow_states(self, team_id: str) -> List[Dict]:
        """Get workflow states for a team."""
        query = """
        query($teamId: String!) {
            team(id: $teamId) {
                states {
                    nodes {
                        id
                        name
                        type
                    }
                }
            }
        }
        """
        result = await self._graphql(query, {"teamId": team_id})
        return result.get("team", {}).get("states", {}).get("nodes", [])

    async def create_issue(
        self,
        team_id: str,
        title: str,
        description: str = "",
        priority: int = 0,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None
    ) -> Dict:
        """
        Create a Linear issue.

        Args:
            team_id: Team ID
            title: Issue title
            description: Issue description (markdown)
            priority: Priority (0=none, 1=urgent, 2=high, 3=medium, 4=low)
            project_id: Optional project ID
            assignee_id: Optional assignee ID

        Returns:
            Created issue data
        """
        query = """
        mutation($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """

        input_data = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority
        }

        if project_id:
            input_data["projectId"] = project_id
        if assignee_id:
            input_data["assigneeId"] = assignee_id

        result = await self._graphql(query, {"input": input_data})
        return result.get("issueCreate", {}).get("issue", {})

    async def update_issue(
        self,
        issue_id: str,
        state_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict:
        """Update an issue."""
        query = """
        mutation($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    state {
                        name
                    }
                }
            }
        }
        """

        input_data = {}
        if state_id:
            input_data["stateId"] = state_id
        if title:
            input_data["title"] = title
        if description:
            input_data["description"] = description

        result = await self._graphql(query, {"id": issue_id, "input": input_data})
        return result.get("issueUpdate", {}).get("issue", {})

    async def sync_action_item(
        self,
        action_item: Any,
        team_id: str,
        project_id: Optional[str] = None
    ) -> Dict:
        """
        Sync a ReadIn action item to Linear.

        Args:
            action_item: ActionItem model instance
            team_id: Target Linear team ID
            project_id: Optional project ID

        Returns:
            Created Linear issue data
        """
        description = f"From ReadIn AI meeting\n\n{action_item.description or ''}"

        if action_item.due_date:
            description += f"\n\n**Due:** {action_item.due_date.strftime('%Y-%m-%d')}"

        # Map priority (Linear: 0=none, 1=urgent, 2=high, 3=medium, 4=low)
        priority_map = {
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        priority = priority_map.get(action_item.priority, 0)

        issue = await self.create_issue(
            team_id=team_id,
            title=action_item.title,
            description=description,
            priority=priority,
            project_id=project_id
        )

        logger.info(f"Synced action item {action_item.id} to Linear issue {issue.get('identifier')}")
        return issue

    async def sync_all_pending(
        self,
        action_items: List[Any],
        team_id: str,
        project_id: Optional[str] = None
    ) -> List[Dict]:
        """Sync multiple action items."""
        results = []
        for item in action_items:
            if item.status in ["pending", "in_progress"]:
                try:
                    issue = await self.sync_action_item(item, team_id, project_id)
                    results.append({"item_id": str(item.id), "linear_issue": issue})
                except Exception as e:
                    logger.error(f"Failed to sync action item {item.id}: {e}")
                    results.append({"item_id": str(item.id), "error": str(e)})
        return results


def get_linear_oauth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Generate Linear OAuth URL."""
    return (
        f"https://linear.app/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=read,write"
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
            "https://api.linear.app/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
        )
        return response.json()
