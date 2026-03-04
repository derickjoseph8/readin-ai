"""
Project Management Sync Service for ReadIn AI.

Handles automatic synchronization of action items with external
project management tools like Notion, Asana, Linear, and Jira.

This service is called when:
- Action items are created
- Action items are updated
- Status changes in external systems need to be synced back
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from models import (
    ActionItem,
    ProjectManagementConnection,
    ActionItemSync,
    IntegrationProvider,
)
from integrations.project_management.base import TaskData, TaskStatus, SyncResult
from integrations.project_management.notion import NotionIntegration
from integrations.project_management.asana import AsanaIntegration
from integrations.project_management.linear import LinearIntegration
from integrations.project_management.jira import JiraIntegration
from integrations.project_management.monday import MondayIntegration

logger = logging.getLogger("pm_sync_service")


class PMSyncService:
    """
    Service for syncing action items with project management tools.

    Provides methods for:
    - Auto-syncing new action items
    - Updating existing synced items
    - Syncing status changes bidirectionally
    - Batch sync operations
    """

    def __init__(self, db: Session):
        self.db = db

    def _get_integration(
        self,
        provider: str,
        connection: ProjectManagementConnection,
    ):
        """Create an integration instance for the given provider."""
        if provider == IntegrationProvider.NOTION:
            return NotionIntegration(
                db=self.db,
                access_token=connection.access_token,
                refresh_token=connection.refresh_token,
                database_id=connection.project_id,
            )
        elif provider == IntegrationProvider.ASANA:
            return AsanaIntegration(
                db=self.db,
                access_token=connection.access_token,
                refresh_token=connection.refresh_token,
                workspace_gid=connection.workspace_id,
                project_gid=connection.project_id,
            )
        elif provider == IntegrationProvider.LINEAR:
            return LinearIntegration(
                db=self.db,
                access_token=connection.access_token,
                refresh_token=connection.refresh_token,
                team_id=connection.project_id,
            )
        elif provider == IntegrationProvider.JIRA:
            return JiraIntegration(
                db=self.db,
                access_token=connection.access_token,
                refresh_token=connection.refresh_token,
                cloud_id=connection.workspace_id,
                project_key=connection.project_id,
            )
        elif provider == IntegrationProvider.MONDAY:
            return MondayIntegration(
                db=self.db,
                access_token=connection.access_token,
                refresh_token=connection.refresh_token,
                board_id=connection.project_id,
                group_id=connection.workspace_id,  # Using workspace_id for group_id
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def auto_sync_action_item(
        self,
        action_item: ActionItem,
        user_id: int,
    ) -> Dict[str, SyncResult]:
        """
        Automatically sync an action item to all connected PM tools
        that have auto-sync enabled.

        Args:
            action_item: The ActionItem to sync
            user_id: The user's ID

        Returns:
            Dictionary mapping provider names to SyncResults
        """
        results = {}

        # Get all active PM connections with auto-sync enabled
        connections = self.db.query(ProjectManagementConnection).filter(
            ProjectManagementConnection.user_id == user_id,
            ProjectManagementConnection.is_active == True,
            ProjectManagementConnection.auto_sync_enabled == True,
            ProjectManagementConnection.project_id.isnot(None),
        ).all()

        if not connections:
            logger.debug(f"No auto-sync PM connections for user {user_id}")
            return results

        task_data = TaskData.from_action_item(action_item)

        for connection in connections:
            try:
                # Check for existing sync
                existing_sync = self.db.query(ActionItemSync).filter(
                    ActionItemSync.action_item_id == action_item.id,
                    ActionItemSync.connection_id == connection.id
                ).first()

                integration = self._get_integration(connection.provider, connection)

                try:
                    if existing_sync:
                        # Update existing task
                        result = await integration.update_task(
                            existing_sync.external_id,
                            task_data
                        )
                        if result.success:
                            existing_sync.last_synced_at = datetime.utcnow()
                            existing_sync.sync_errors = 0
                            existing_sync.last_error = None
                        else:
                            existing_sync.sync_errors += 1
                            existing_sync.last_error = result.error
                    else:
                        # Create new task
                        result = await integration.create_task(task_data)
                        if result.success:
                            sync_record = ActionItemSync(
                                action_item_id=action_item.id,
                                connection_id=connection.id,
                                external_id=result.external_id,
                                external_url=result.external_url,
                            )
                            self.db.add(sync_record)

                    results[connection.provider] = result

                    # Update connection sync timestamp
                    connection.last_sync_at = datetime.utcnow()
                    if not result.success:
                        connection.error_count += 1
                        connection.last_error = result.error

                finally:
                    await integration.close()

            except Exception as e:
                logger.error(f"Error syncing to {connection.provider}: {e}")
                results[connection.provider] = SyncResult(
                    success=False,
                    error=str(e)
                )
                connection.error_count += 1
                connection.last_error = str(e)

        self.db.commit()
        return results

    async def sync_status_update(
        self,
        action_item: ActionItem,
        new_status: str,
    ) -> Dict[str, SyncResult]:
        """
        Sync a status change to all connected PM tools.

        Args:
            action_item: The ActionItem with updated status
            new_status: The new status value

        Returns:
            Dictionary mapping provider names to SyncResults
        """
        results = {}

        # Get all syncs for this action item
        syncs = self.db.query(ActionItemSync).filter(
            ActionItemSync.action_item_id == action_item.id
        ).all()

        if not syncs:
            return results

        task_data = TaskData.from_action_item(action_item)

        for sync in syncs:
            connection = self.db.query(ProjectManagementConnection).filter(
                ProjectManagementConnection.id == sync.connection_id,
                ProjectManagementConnection.is_active == True,
            ).first()

            if not connection or not connection.sync_completed_status:
                continue

            try:
                integration = self._get_integration(connection.provider, connection)

                try:
                    result = await integration.update_task(
                        sync.external_id,
                        task_data
                    )

                    if result.success:
                        sync.last_synced_at = datetime.utcnow()
                        sync.last_external_status = new_status
                        sync.sync_errors = 0
                        sync.last_error = None
                    else:
                        sync.sync_errors += 1
                        sync.last_error = result.error

                    results[connection.provider] = result

                finally:
                    await integration.close()

            except Exception as e:
                logger.error(f"Error syncing status to {connection.provider}: {e}")
                results[connection.provider] = SyncResult(
                    success=False,
                    error=str(e)
                )
                sync.sync_errors += 1
                sync.last_error = str(e)

        self.db.commit()
        return results

    async def sync_from_external(
        self,
        user_id: int,
        provider: str,
    ) -> List[Dict[str, Any]]:
        """
        Sync status changes from external PM tool back to ReadIn.

        This checks the status of all synced items and updates
        the local ActionItem status if it has changed.

        Args:
            user_id: The user's ID
            provider: The PM provider to sync from

        Returns:
            List of items that were updated
        """
        updated_items = []

        connection = self.db.query(ProjectManagementConnection).filter(
            ProjectManagementConnection.user_id == user_id,
            ProjectManagementConnection.provider == provider,
            ProjectManagementConnection.is_active == True,
        ).first()

        if not connection:
            return updated_items

        # Get all syncs for this connection
        syncs = self.db.query(ActionItemSync).filter(
            ActionItemSync.connection_id == connection.id
        ).all()

        if not syncs:
            return updated_items

        integration = self._get_integration(provider, connection)

        try:
            for sync in syncs:
                action_item = self.db.query(ActionItem).filter(
                    ActionItem.id == sync.action_item_id
                ).first()

                if not action_item:
                    continue

                try:
                    external_status = await integration.sync_status(sync.external_id)
                    if external_status:
                        # Map external status to internal status
                        internal_status = self._map_external_status(external_status)

                        if internal_status != action_item.status:
                            old_status = action_item.status
                            action_item.status = internal_status

                            if internal_status == "completed":
                                action_item.completed_at = datetime.utcnow()

                            sync.last_synced_at = datetime.utcnow()
                            sync.last_external_status = external_status.value

                            updated_items.append({
                                "action_item_id": action_item.id,
                                "old_status": old_status,
                                "new_status": internal_status,
                                "external_status": external_status.value,
                            })

                except Exception as e:
                    logger.error(f"Error syncing item {sync.external_id}: {e}")
                    sync.sync_errors += 1
                    sync.last_error = str(e)

        finally:
            await integration.close()

        self.db.commit()
        return updated_items

    def _map_external_status(self, external_status: TaskStatus) -> str:
        """Map external TaskStatus to internal status string."""
        mapping = {
            TaskStatus.PENDING: "pending",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.COMPLETED: "completed",
            TaskStatus.CANCELLED: "cancelled",
        }
        return mapping.get(external_status, "pending")

    async def delete_external_task(
        self,
        action_item_id: int,
        provider: Optional[str] = None,
    ) -> Dict[str, SyncResult]:
        """
        Delete/archive tasks in external systems when action item is deleted.

        Args:
            action_item_id: The action item being deleted
            provider: Optional specific provider to delete from

        Returns:
            Dictionary mapping provider names to SyncResults
        """
        results = {}

        query = self.db.query(ActionItemSync).filter(
            ActionItemSync.action_item_id == action_item_id
        )

        syncs = query.all()

        for sync in syncs:
            connection = self.db.query(ProjectManagementConnection).filter(
                ProjectManagementConnection.id == sync.connection_id,
                ProjectManagementConnection.is_active == True,
            ).first()

            if not connection:
                continue

            if provider and connection.provider != provider:
                continue

            try:
                integration = self._get_integration(connection.provider, connection)

                try:
                    result = await integration.delete_task(sync.external_id)
                    results[connection.provider] = result

                    if result.success:
                        # Remove sync record
                        self.db.delete(sync)

                finally:
                    await integration.close()

            except Exception as e:
                logger.error(f"Error deleting from {connection.provider}: {e}")
                results[connection.provider] = SyncResult(
                    success=False,
                    error=str(e)
                )

        self.db.commit()
        return results

    def get_sync_summary(
        self,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Get a summary of sync status for a user.

        Args:
            user_id: The user's ID

        Returns:
            Summary dictionary with counts and status
        """
        connections = self.db.query(ProjectManagementConnection).filter(
            ProjectManagementConnection.user_id == user_id,
            ProjectManagementConnection.is_active == True,
        ).all()

        summary = {
            "connected_providers": len(connections),
            "providers": [],
            "total_synced_items": 0,
            "items_with_errors": 0,
        }

        for connection in connections:
            sync_count = self.db.query(ActionItemSync).filter(
                ActionItemSync.connection_id == connection.id
            ).count()

            error_count = self.db.query(ActionItemSync).filter(
                ActionItemSync.connection_id == connection.id,
                ActionItemSync.sync_errors > 0
            ).count()

            summary["total_synced_items"] += sync_count
            summary["items_with_errors"] += error_count

            summary["providers"].append({
                "provider": connection.provider,
                "workspace_name": connection.workspace_name,
                "project_name": connection.project_name,
                "auto_sync_enabled": connection.auto_sync_enabled,
                "synced_items": sync_count,
                "items_with_errors": error_count,
                "last_sync_at": connection.last_sync_at,
                "last_error": connection.last_error,
            })

        return summary


# Helper function for use in routes/tasks.py
async def trigger_action_item_sync(
    db: Session,
    action_item: ActionItem,
    user_id: int,
) -> None:
    """
    Trigger auto-sync for an action item.

    Call this after creating or updating an action item.
    """
    try:
        sync_service = PMSyncService(db)
        await sync_service.auto_sync_action_item(action_item, user_id)
    except Exception as e:
        logger.error(f"Error triggering auto-sync: {e}")
        # Don't raise - auto-sync failures shouldn't block main operations


async def trigger_status_sync(
    db: Session,
    action_item: ActionItem,
    new_status: str,
) -> None:
    """
    Trigger status sync when an action item status changes.

    Call this after updating an action item's status.
    """
    try:
        sync_service = PMSyncService(db)
        await sync_service.sync_status_update(action_item, new_status)
    except Exception as e:
        logger.error(f"Error triggering status sync: {e}")
        # Don't raise - sync failures shouldn't block main operations
