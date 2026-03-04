"""
Project Management Integrations for ReadIn AI.

Supports syncing action items and tasks with:
- Notion
- Asana
- Linear
- Jira
- Monday.com

Each integration implements the ProjectManagementIntegration base class
to provide consistent task sync functionality.
"""

from integrations.project_management.base import (
    ProjectManagementIntegration,
    TaskStatus,
    TaskPriority,
    SyncResult,
    TaskData,
)
from integrations.project_management.notion import NotionIntegration
from integrations.project_management.asana import AsanaIntegration
from integrations.project_management.linear import LinearIntegration
from integrations.project_management.jira import JiraIntegration
from integrations.project_management.monday import MondayIntegration

__all__ = [
    "ProjectManagementIntegration",
    "TaskStatus",
    "TaskPriority",
    "SyncResult",
    "TaskData",
    "NotionIntegration",
    "AsanaIntegration",
    "LinearIntegration",
    "JiraIntegration",
    "MondayIntegration",
]
