"""
Base class for Project Management integrations.

Provides a consistent interface for syncing action items with
external project management tools like Notion, Asana, Linear, and Jira.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger("project_management")


class TaskStatus(str, Enum):
    """Normalized task statuses across all integrations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Normalized task priorities across all integrations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TaskData:
    """
    Normalized task/action item data for sync operations.

    This serves as the bridge between ReadIn's ActionItem model
    and external project management systems.
    """
    id: int  # Internal ReadIn action item ID
    title: str
    description: Optional[str] = None
    assignee: Optional[str] = None
    assignee_email: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    meeting_id: Optional[int] = None
    meeting_title: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_action_item(cls, action_item) -> "TaskData":
        """
        Create TaskData from a ReadIn ActionItem model instance.

        Args:
            action_item: SQLAlchemy ActionItem model instance

        Returns:
            TaskData instance with normalized fields
        """
        # Map internal status to TaskStatus
        status_map = {
            "pending": TaskStatus.PENDING,
            "in_progress": TaskStatus.IN_PROGRESS,
            "completed": TaskStatus.COMPLETED,
            "cancelled": TaskStatus.CANCELLED,
        }

        # Map internal priority to TaskPriority
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT,
        }

        return cls(
            id=action_item.id,
            title=action_item.description[:100] if action_item.description else "Untitled Task",
            description=action_item.description,
            assignee=action_item.assignee,
            assignee_email=getattr(action_item, 'assignee_email', None),
            due_date=action_item.due_date,
            priority=priority_map.get(action_item.priority, TaskPriority.MEDIUM),
            status=status_map.get(action_item.status, TaskStatus.PENDING),
            meeting_id=action_item.meeting_id,
            meeting_title=action_item.meeting.title if hasattr(action_item, 'meeting') and action_item.meeting else None,
            labels=["ReadIn AI", "Action Item"],
            metadata={
                "readin_action_item_id": action_item.id,
                "created_at": action_item.created_at.isoformat() if action_item.created_at else None,
            }
        )


@dataclass
class SyncResult:
    """Result of a sync operation with an external system."""
    success: bool
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectManagementIntegration(ABC):
    """
    Base class for project management integrations.

    All project management integrations (Notion, Asana, Linear, Jira)
    should inherit from this class and implement its abstract methods.

    Provides:
    - OAuth flow helpers
    - Task creation, update, and sync
    - Status mapping
    - Error handling
    """

    # Class attributes to be set by subclasses
    PROVIDER_NAME: str = "base"
    DISPLAY_NAME: str = "Base Integration"
    OAUTH_AUTHORIZE_URL: str = ""
    OAUTH_TOKEN_URL: str = ""
    API_BASE_URL: str = ""

    def __init__(
        self,
        db: Session,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        """
        Initialize the integration.

        Args:
            db: SQLAlchemy database session
            access_token: OAuth access token for API calls
            refresh_token: OAuth refresh token for token refresh
        """
        self.db = db
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with default headers."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers=self._get_default_headers(),
            )
        return self._client

    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ReadIn-AI/1.0",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    @abstractmethod
    def get_oauth_url(self, user_id: int, redirect_uri: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            user_id: User ID for state parameter
            redirect_uri: Callback URL after authorization

        Returns:
            OAuth authorization URL
        """
        raise NotImplementedError

    @abstractmethod
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Must match the one used in authorization

        Returns:
            Dictionary with access_token, refresh_token, etc.
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_access_token(self) -> Optional[str]:
        """
        Refresh the access token using the refresh token.

        Returns:
            New access token or None if refresh failed
        """
        raise NotImplementedError

    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================

    @abstractmethod
    async def create_task(self, task: TaskData) -> SyncResult:
        """
        Create a task in the external system.

        Args:
            task: TaskData with task details

        Returns:
            SyncResult with external_id if successful
        """
        raise NotImplementedError

    @abstractmethod
    async def update_task(
        self,
        external_id: str,
        task: TaskData,
    ) -> SyncResult:
        """
        Update an existing task in the external system.

        Args:
            external_id: Task ID in the external system
            task: Updated TaskData

        Returns:
            SyncResult indicating success/failure
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_task(self, external_id: str) -> SyncResult:
        """
        Delete/archive a task in the external system.

        Args:
            external_id: Task ID in the external system

        Returns:
            SyncResult indicating success/failure
        """
        raise NotImplementedError

    @abstractmethod
    async def sync_status(self, external_id: str) -> Optional[TaskStatus]:
        """
        Get the current status of a task from the external system.

        Args:
            external_id: Task ID in the external system

        Returns:
            Normalized TaskStatus or None if not found
        """
        raise NotImplementedError

    @abstractmethod
    async def get_task(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task details from the external system.

        Args:
            external_id: Task ID in the external system

        Returns:
            Task data dictionary or None if not found
        """
        raise NotImplementedError

    # =========================================================================
    # WORKSPACE/PROJECT METHODS
    # =========================================================================

    @abstractmethod
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """
        List available workspaces/organizations.

        Returns:
            List of workspace dictionaries with id, name, etc.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_projects(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List projects/databases within a workspace.

        Args:
            workspace_id: Optional workspace filter

        Returns:
            List of project dictionaries with id, name, etc.
        """
        raise NotImplementedError

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def map_priority_to_external(self, priority: TaskPriority) -> Any:
        """
        Map internal priority to external system's priority format.

        Override in subclasses for provider-specific mapping.

        Args:
            priority: Internal TaskPriority

        Returns:
            Provider-specific priority value
        """
        return priority.value

    def map_priority_from_external(self, external_priority: Any) -> TaskPriority:
        """
        Map external system's priority to internal TaskPriority.

        Override in subclasses for provider-specific mapping.

        Args:
            external_priority: Provider-specific priority value

        Returns:
            Normalized TaskPriority
        """
        return TaskPriority.MEDIUM

    def map_status_to_external(self, status: TaskStatus) -> Any:
        """
        Map internal status to external system's status format.

        Override in subclasses for provider-specific mapping.

        Args:
            status: Internal TaskStatus

        Returns:
            Provider-specific status value
        """
        return status.value

    def map_status_from_external(self, external_status: Any) -> TaskStatus:
        """
        Map external system's status to internal TaskStatus.

        Override in subclasses for provider-specific mapping.

        Args:
            external_status: Provider-specific status value

        Returns:
            Normalized TaskStatus
        """
        return TaskStatus.PENDING

    async def test_connection(self) -> bool:
        """
        Test if the integration connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            workspaces = await self.list_workspaces()
            return len(workspaces) > 0
        except Exception as e:
            logger.error(f"Connection test failed for {self.PROVIDER_NAME}: {e}")
            return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(provider={self.PROVIDER_NAME})>"
