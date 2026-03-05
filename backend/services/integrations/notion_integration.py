"""
Notion Integration - Sync meetings and notes with Notion.
"""

import logging
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger(__name__)


class NotionIntegration:
    """Notion API integration for syncing meetings."""

    BASE_URL = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request to Notion."""
        url = f"{self.BASE_URL}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )

            if response.status_code >= 400:
                logger.error(f"Notion API error: {response.status_code} - {response.text}")
                raise Exception(f"Notion API error: {response.status_code}")

            return response.json()

    async def search_databases(self, query: str = "") -> List[Dict]:
        """Search for databases accessible to the integration."""
        data = {
            "filter": {"property": "object", "value": "database"}
        }
        if query:
            data["query"] = query

        result = await self._request("POST", "search", data)
        return result.get("results", [])

    async def get_database(self, database_id: str) -> Dict:
        """Get database details."""
        return await self._request("GET", f"databases/{database_id}")

    async def create_page(
        self,
        database_id: str,
        properties: Dict,
        children: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Create a page in a Notion database.

        Args:
            database_id: Target database ID
            properties: Page properties (title, date, etc.)
            children: Content blocks

        Returns:
            Created page data
        """
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }

        if children:
            data["children"] = children

        return await self._request("POST", "pages", data)

    async def append_blocks(self, page_id: str, blocks: List[Dict]) -> Dict:
        """Append content blocks to a page."""
        return await self._request(
            "PATCH",
            f"blocks/{page_id}/children",
            {"children": blocks}
        )

    async def sync_meeting(
        self,
        meeting: Any,
        database_id: str,
        transcript: Optional[str] = None
    ) -> Dict:
        """
        Sync a ReadIn meeting to Notion.

        Args:
            meeting: Meeting model instance
            database_id: Target Notion database
            transcript: Optional transcript text

        Returns:
            Created Notion page data
        """
        # Build properties based on common database schemas
        properties = {
            "Name": {
                "title": [{"text": {"content": meeting.title or "Meeting"}}]
            },
            "Date": {
                "date": {"start": meeting.start_time.isoformat()}
            }
        }

        # Build content blocks
        children = []

        # Summary section
        if meeting.summary:
            children.extend([
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Summary"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": meeting.summary}}]
                    }
                }
            ])

        # Key points
        if meeting.key_points:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Key Points"}}]
                }
            })
            for point in meeting.key_points:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": point}}]
                    }
                })

        # Action items
        if hasattr(meeting, 'action_items') and meeting.action_items:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Action Items"}}]
                }
            })
            for item in meeting.action_items:
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": item.title}}],
                        "checked": item.status == "completed"
                    }
                })

        # Transcript (truncated if too long)
        if transcript:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"text": {"content": "Transcript"}}]
                }
            })
            # Split into chunks (Notion has block size limits)
            chunks = [transcript[i:i+2000] for i in range(0, len(transcript), 2000)]
            for chunk in chunks[:10]:  # Limit to 10 chunks
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": chunk}}]
                    }
                })

        page = await self.create_page(database_id, properties, children)
        logger.info(f"Synced meeting {meeting.id} to Notion page {page.get('id')}")
        return page


def get_notion_oauth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Generate Notion OAuth URL."""
    return (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&owner=user"
        f"&state={state}"
    )


async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> Dict:
    """Exchange OAuth code for access token."""
    import base64

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.notion.com/v1/oauth/token",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json"
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        return response.json()
