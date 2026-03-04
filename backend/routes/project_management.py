"""
Project Management Integration Routes for ReadIn AI.

Provides API endpoints for:
- Connecting to project management tools (Notion, Asana, Linear, Jira)
- Syncing action items with external systems
- Managing integration settings

All routes require authentication.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User,
    ActionItem,
    IntegrationProvider,
    ProjectManagementConnection,
    ActionItemSync,
)
from auth import get_current_user
from config import APP_URL

from integrations.project_management.notion import NotionIntegration, is_notion_configured
from integrations.project_management.asana import AsanaIntegration, is_asana_configured
from integrations.project_management.linear import LinearIntegration, is_linear_configured
from integrations.project_management.jira import JiraIntegration, is_jira_configured
from integrations.project_management.monday import MondayIntegration, is_monday_configured
from integrations.project_management.base import TaskData, SyncResult

logger = logging.getLogger("project_management_routes")
router = APIRouter(prefix="/integrations/pm", tags=["Project Management"])


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class PMIntegrationStatus(BaseModel):
    """Status of a project management integration."""
    provider: str
    display_name: str
    is_configured: bool
    is_connected: bool
    workspace_name: Optional[str] = None
    project_name: Optional[str] = None
    auto_sync_enabled: bool = True
    connected_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    error: Optional[str] = None


class PMIntegrationSettings(BaseModel):
    """Settings for a project management integration."""
    auto_sync_enabled: bool = True
    sync_completed_status: bool = True
    sync_priority: bool = True
    default_labels: Optional[List[str]] = None


class SelectWorkspaceRequest(BaseModel):
    """Request to select a workspace/organization."""
    workspace_id: str
    workspace_name: Optional[str] = None


class SelectProjectRequest(BaseModel):
    """Request to select a project/database."""
    project_id: str
    project_name: Optional[str] = None


class SyncActionItemRequest(BaseModel):
    """Request to sync a specific action item."""
    action_item_id: int


class BulkSyncRequest(BaseModel):
    """Request to sync multiple action items."""
    action_item_ids: List[int]


class SyncResponse(BaseModel):
    """Response for sync operations."""
    success: bool
    synced_count: int = 0
    failed_count: int = 0
    results: List[dict] = []


# =============================================================================
# PROVIDER HELPERS
# =============================================================================

PM_PROVIDERS = {
    IntegrationProvider.NOTION: {
        "display_name": "Notion",
        "is_configured": is_notion_configured,
        "integration_class": NotionIntegration,
    },
    IntegrationProvider.ASANA: {
        "display_name": "Asana",
        "is_configured": is_asana_configured,
        "integration_class": AsanaIntegration,
    },
    IntegrationProvider.LINEAR: {
        "display_name": "Linear",
        "is_configured": is_linear_configured,
        "integration_class": LinearIntegration,
    },
    IntegrationProvider.JIRA: {
        "display_name": "Jira",
        "is_configured": is_jira_configured,
        "integration_class": JiraIntegration,
    },
    IntegrationProvider.MONDAY: {
        "display_name": "Monday.com",
        "is_configured": is_monday_configured,
        "integration_class": MondayIntegration,
    },
}


def get_integration_instance(
    provider: str,
    connection: ProjectManagementConnection,
    db: Session,
):
    """Create an integration instance with the user's connection details."""
    if provider == IntegrationProvider.NOTION:
        return NotionIntegration(
            db=db,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            database_id=connection.project_id,
        )
    elif provider == IntegrationProvider.ASANA:
        return AsanaIntegration(
            db=db,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            workspace_gid=connection.workspace_id,
            project_gid=connection.project_id,
        )
    elif provider == IntegrationProvider.LINEAR:
        return LinearIntegration(
            db=db,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            team_id=connection.project_id,
        )
    elif provider == IntegrationProvider.JIRA:
        return JiraIntegration(
            db=db,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            cloud_id=connection.workspace_id,
            project_key=connection.project_id,
        )
    elif provider == IntegrationProvider.MONDAY:
        return MondayIntegration(
            db=db,
            access_token=connection.access_token,
            refresh_token=connection.refresh_token,
            board_id=connection.project_id,
            group_id=connection.workspace_id,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# LIST AVAILABLE INTEGRATIONS
# =============================================================================

@router.get("/available")
async def get_available_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all available project management integrations
    and their connection status for the current user.
    """
    integrations = []

    # Get user's connections
    user_connections = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.is_active == True
    ).all()

    connection_map = {c.provider: c for c in user_connections}

    for provider, info in PM_PROVIDERS.items():
        connection = connection_map.get(provider)
        integrations.append(PMIntegrationStatus(
            provider=provider,
            display_name=info["display_name"],
            is_configured=info["is_configured"](),
            is_connected=connection is not None,
            workspace_name=connection.workspace_name if connection else None,
            project_name=connection.project_name if connection else None,
            auto_sync_enabled=connection.auto_sync_enabled if connection else True,
            connected_at=connection.connected_at if connection else None,
            last_sync_at=connection.last_sync_at if connection else None,
            error=connection.last_error if connection else None,
        ))

    return {"integrations": integrations}


# =============================================================================
# NOTION INTEGRATION
# =============================================================================

@router.get("/notion/authorize")
async def notion_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Notion OAuth authorization URL."""
    if not is_notion_configured():
        raise HTTPException(status_code=503, detail="Notion integration not configured")

    notion = NotionIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/notion/callback"
    auth_url = notion.get_oauth_url(current_user.id, redirect_uri)
    await notion.close()

    return {"authorization_url": auth_url}


@router.get("/notion/callback")
async def notion_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Notion OAuth callback."""
    if not is_notion_configured():
        raise HTTPException(status_code=503, detail="Notion integration not configured")

    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    notion = NotionIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/notion/callback"
    result = await notion.exchange_code(code, redirect_uri)
    await notion.close()

    if not result.get("success"):
        logger.error(f"Notion OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=notion_auth_failed"}
        )

    # Check for existing connection
    existing = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == user_id,
        ProjectManagementConnection.provider == IntegrationProvider.NOTION
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.workspace_id = result.get("workspace_id")
        existing.workspace_name = result.get("workspace_name")
        existing.provider_user_id = result.get("bot_id")
        existing.is_active = True
        existing.last_error = None
        existing.error_count = 0
        existing.updated_at = datetime.utcnow()
    else:
        connection = ProjectManagementConnection(
            user_id=user_id,
            provider=IntegrationProvider.NOTION,
            access_token=result.get("access_token"),
            workspace_id=result.get("workspace_id"),
            workspace_name=result.get("workspace_name"),
            provider_user_id=result.get("bot_id"),
        )
        db.add(connection)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=notion_connected"}
    )


@router.get("/notion/databases")
async def list_notion_databases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available Notion databases for task sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.NOTION,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Notion not connected")

    notion = NotionIntegration(
        db=db,
        access_token=connection.access_token,
    )
    databases = await notion.list_projects()
    await notion.close()

    return {"databases": databases}


@router.post("/notion/select-database")
async def select_notion_database(
    request: SelectProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Notion database for task sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.NOTION,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Notion not connected")

    connection.project_id = request.project_id
    connection.project_name = request.project_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Database selected", "database_id": request.project_id}


@router.delete("/notion")
async def disconnect_notion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Notion integration."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.NOTION
    ).first()

    if connection:
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Notion disconnected"}


# =============================================================================
# ASANA INTEGRATION
# =============================================================================

@router.get("/asana/authorize")
async def asana_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Asana OAuth authorization URL."""
    if not is_asana_configured():
        raise HTTPException(status_code=503, detail="Asana integration not configured")

    asana = AsanaIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/asana/callback"
    auth_url = asana.get_oauth_url(current_user.id, redirect_uri)
    await asana.close()

    return {"authorization_url": auth_url}


@router.get("/asana/callback")
async def asana_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Asana OAuth callback."""
    if not is_asana_configured():
        raise HTTPException(status_code=503, detail="Asana integration not configured")

    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    asana = AsanaIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/asana/callback"
    result = await asana.exchange_code(code, redirect_uri)
    await asana.close()

    if not result.get("success"):
        logger.error(f"Asana OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=asana_auth_failed"}
        )

    existing = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == user_id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        existing.provider_user_id = result.get("user_gid")
        existing.provider_user_email = result.get("user_email")
        existing.is_active = True
        existing.last_error = None
        existing.error_count = 0
        existing.updated_at = datetime.utcnow()
    else:
        connection = ProjectManagementConnection(
            user_id=user_id,
            provider=IntegrationProvider.ASANA,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            provider_user_id=result.get("user_gid"),
            provider_user_email=result.get("user_email"),
        )
        db.add(connection)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=asana_connected"}
    )


@router.get("/asana/workspaces")
async def list_asana_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Asana workspaces."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Asana not connected")

    asana = AsanaIntegration(
        db=db,
        access_token=connection.access_token,
        refresh_token=connection.refresh_token,
    )
    workspaces = await asana.list_workspaces()
    await asana.close()

    return {"workspaces": workspaces}


@router.post("/asana/select-workspace")
async def select_asana_workspace(
    request: SelectWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select an Asana workspace."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Asana not connected")

    connection.workspace_id = request.workspace_id
    connection.workspace_name = request.workspace_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Workspace selected", "workspace_id": request.workspace_id}


@router.get("/asana/projects")
async def list_asana_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Asana projects in the selected workspace."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Asana not connected")

    if not connection.workspace_id:
        raise HTTPException(status_code=400, detail="No workspace selected")

    asana = AsanaIntegration(
        db=db,
        access_token=connection.access_token,
        refresh_token=connection.refresh_token,
        workspace_gid=connection.workspace_id,
    )
    projects = await asana.list_projects()
    await asana.close()

    return {"projects": projects}


@router.post("/asana/select-project")
async def select_asana_project(
    request: SelectProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select an Asana project for task sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Asana not connected")

    connection.project_id = request.project_id
    connection.project_name = request.project_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Project selected", "project_id": request.project_id}


@router.delete("/asana")
async def disconnect_asana(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Asana integration."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.ASANA
    ).first()

    if connection:
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Asana disconnected"}


# =============================================================================
# LINEAR INTEGRATION
# =============================================================================

@router.get("/linear/authorize")
async def linear_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Linear OAuth authorization URL."""
    if not is_linear_configured():
        raise HTTPException(status_code=503, detail="Linear integration not configured")

    linear = LinearIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/linear/callback"
    auth_url = linear.get_oauth_url(current_user.id, redirect_uri)
    await linear.close()

    return {"authorization_url": auth_url}


@router.get("/linear/callback")
async def linear_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Linear OAuth callback."""
    if not is_linear_configured():
        raise HTTPException(status_code=503, detail="Linear integration not configured")

    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    linear = LinearIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/linear/callback"
    result = await linear.exchange_code(code, redirect_uri)
    await linear.close()

    if not result.get("success"):
        logger.error(f"Linear OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=linear_auth_failed"}
        )

    existing = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == user_id,
        ProjectManagementConnection.provider == IntegrationProvider.LINEAR
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.is_active = True
        existing.last_error = None
        existing.error_count = 0
        existing.updated_at = datetime.utcnow()
    else:
        connection = ProjectManagementConnection(
            user_id=user_id,
            provider=IntegrationProvider.LINEAR,
            access_token=result.get("access_token"),
        )
        db.add(connection)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=linear_connected"}
    )


@router.get("/linear/teams")
async def list_linear_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Linear teams."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.LINEAR,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Linear not connected")

    linear = LinearIntegration(
        db=db,
        access_token=connection.access_token,
    )
    teams = await linear.list_projects()
    await linear.close()

    return {"teams": teams}


@router.post("/linear/select-team")
async def select_linear_team(
    request: SelectProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Linear team for issue sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.LINEAR,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Linear not connected")

    connection.project_id = request.project_id
    connection.project_name = request.project_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Team selected", "team_id": request.project_id}


@router.delete("/linear")
async def disconnect_linear(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Linear integration."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.LINEAR
    ).first()

    if connection:
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Linear disconnected"}


# =============================================================================
# JIRA INTEGRATION
# =============================================================================

@router.get("/jira/authorize")
async def jira_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Jira OAuth authorization URL."""
    if not is_jira_configured():
        raise HTTPException(status_code=503, detail="Jira integration not configured")

    jira = JiraIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/jira/callback"
    auth_url = jira.get_oauth_url(current_user.id, redirect_uri)
    await jira.close()

    return {"authorization_url": auth_url}


@router.get("/jira/callback")
async def jira_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Jira OAuth callback."""
    if not is_jira_configured():
        raise HTTPException(status_code=503, detail="Jira integration not configured")

    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    jira = JiraIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/jira/callback"
    result = await jira.exchange_code(code, redirect_uri)
    await jira.close()

    if not result.get("success"):
        logger.error(f"Jira OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=jira_auth_failed"}
        )

    # Get the first available site
    sites = result.get("sites", [])
    site = sites[0] if sites else None

    existing = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == user_id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.refresh_token = result.get("refresh_token")
        existing.token_expires_at = datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600))
        if site:
            existing.workspace_id = site.get("id")
            existing.workspace_name = site.get("name")
        existing.is_active = True
        existing.last_error = None
        existing.error_count = 0
        existing.updated_at = datetime.utcnow()
    else:
        connection = ProjectManagementConnection(
            user_id=user_id,
            provider=IntegrationProvider.JIRA,
            access_token=result.get("access_token"),
            refresh_token=result.get("refresh_token"),
            token_expires_at=datetime.utcnow() + timedelta(seconds=result.get("expires_in", 3600)),
            workspace_id=site.get("id") if site else None,
            workspace_name=site.get("name") if site else None,
        )
        db.add(connection)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=jira_connected"}
    )


@router.get("/jira/sites")
async def list_jira_sites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Jira sites (cloud instances)."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Jira not connected")

    jira = JiraIntegration(
        db=db,
        access_token=connection.access_token,
        refresh_token=connection.refresh_token,
    )
    sites = await jira.list_workspaces()
    await jira.close()

    return {"sites": sites}


@router.post("/jira/select-site")
async def select_jira_site(
    request: SelectWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Jira site."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Jira not connected")

    connection.workspace_id = request.workspace_id
    connection.workspace_name = request.workspace_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Site selected", "site_id": request.workspace_id}


@router.get("/jira/projects")
async def list_jira_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Jira projects."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Jira not connected")

    if not connection.workspace_id:
        raise HTTPException(status_code=400, detail="No site selected")

    jira = JiraIntegration(
        db=db,
        access_token=connection.access_token,
        refresh_token=connection.refresh_token,
        cloud_id=connection.workspace_id,
    )
    projects = await jira.list_projects()
    await jira.close()

    return {"projects": projects}


@router.post("/jira/select-project")
async def select_jira_project(
    request: SelectProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Jira project for issue sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Jira not connected")

    # For Jira, project_id is actually the project key
    connection.project_id = request.project_id
    connection.project_name = request.project_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Project selected", "project_key": request.project_id}


@router.delete("/jira")
async def disconnect_jira(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Jira integration."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.JIRA
    ).first()

    if connection:
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Jira disconnected"}


# =============================================================================
# MONDAY.COM INTEGRATION
# =============================================================================

@router.get("/monday/authorize")
async def monday_authorize(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Monday.com OAuth authorization URL."""
    if not is_monday_configured():
        raise HTTPException(status_code=503, detail="Monday.com integration not configured")

    monday = MondayIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/monday/callback"
    auth_url = monday.get_oauth_url(current_user.id, redirect_uri)
    await monday.close()

    return {"authorization_url": auth_url}


@router.get("/monday/callback")
async def monday_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Monday.com OAuth callback."""
    if not is_monday_configured():
        raise HTTPException(status_code=503, detail="Monday.com integration not configured")

    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    monday = MondayIntegration(db)
    redirect_uri = f"{APP_URL}/api/integrations/pm/monday/callback"
    result = await monday.exchange_code(code, redirect_uri)
    await monday.close()

    if not result.get("success"):
        logger.error(f"Monday.com OAuth failed: {result.get('error')}")
        return Response(
            status_code=302,
            headers={"Location": f"{APP_URL}/dashboard/settings/integrations?error=monday_auth_failed"}
        )

    existing = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == user_id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY
    ).first()

    if existing:
        existing.access_token = result.get("access_token")
        existing.provider_user_id = result.get("user_id")
        existing.provider_user_email = result.get("user_email")
        existing.workspace_name = result.get("account_name")
        existing.is_active = True
        existing.last_error = None
        existing.error_count = 0
        existing.updated_at = datetime.utcnow()
    else:
        connection = ProjectManagementConnection(
            user_id=user_id,
            provider=IntegrationProvider.MONDAY,
            access_token=result.get("access_token"),
            provider_user_id=result.get("user_id"),
            provider_user_email=result.get("user_email"),
            workspace_name=result.get("account_name"),
        )
        db.add(connection)

    db.commit()

    return Response(
        status_code=302,
        headers={"Location": f"{APP_URL}/dashboard/settings/integrations?success=monday_connected"}
    )


@router.get("/monday/boards")
async def list_monday_boards(
    workspace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available Monday.com boards."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Monday.com not connected")

    monday = MondayIntegration(
        db=db,
        access_token=connection.access_token,
    )
    boards = await monday.list_projects(workspace_id)
    await monday.close()

    return {"boards": boards}


@router.get("/monday/workspaces")
async def list_monday_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Monday.com workspaces."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Monday.com not connected")

    monday = MondayIntegration(
        db=db,
        access_token=connection.access_token,
    )
    workspaces = await monday.list_workspaces()
    await monday.close()

    return {"workspaces": workspaces}


@router.get("/monday/groups")
async def list_monday_groups(
    board_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List groups within a Monday.com board."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Monday.com not connected")

    monday = MondayIntegration(
        db=db,
        access_token=connection.access_token,
        board_id=board_id,
    )
    groups = await monday.list_groups()
    await monday.close()

    return {"groups": groups}


@router.post("/monday/select-board")
async def select_monday_board(
    request: SelectProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Monday.com board for item sync."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Monday.com not connected")

    connection.project_id = request.project_id
    connection.project_name = request.project_name
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Board selected", "board_id": request.project_id}


@router.post("/monday/select-group")
async def select_monday_group(
    request: SelectWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select a Monday.com group within the selected board."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Monday.com not connected")

    if not connection.project_id:
        raise HTTPException(status_code=400, detail="No board selected")

    # Using workspace_id to store group_id
    connection.workspace_id = request.workspace_id
    connection.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Group selected", "group_id": request.workspace_id}


@router.delete("/monday")
async def disconnect_monday(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Monday.com integration."""
    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == IntegrationProvider.MONDAY
    ).first()

    if connection:
        connection.is_active = False
        connection.updated_at = datetime.utcnow()
        db.commit()

    return {"message": "Monday.com disconnected"}


# =============================================================================
# UNIFIED SYNC OPERATIONS
# =============================================================================

@router.post("/{provider}/sync")
async def sync_action_items(
    provider: str,
    request: BulkSyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync action items to the specified project management provider.

    This creates or updates tasks in the external system based on
    the action items specified.
    """
    if provider not in PM_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == provider,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    if not connection.project_id:
        raise HTTPException(status_code=400, detail="No project/database selected")

    # Get action items
    action_items = db.query(ActionItem).filter(
        ActionItem.id.in_(request.action_item_ids),
        ActionItem.user_id == current_user.id
    ).all()

    if not action_items:
        raise HTTPException(status_code=404, detail="No action items found")

    # Create integration instance
    integration = get_integration_instance(provider, connection, db)

    results = []
    synced_count = 0
    failed_count = 0

    try:
        for action_item in action_items:
            # Check for existing sync
            existing_sync = db.query(ActionItemSync).filter(
                ActionItemSync.action_item_id == action_item.id,
                ActionItemSync.connection_id == connection.id
            ).first()

            # Convert to TaskData
            task_data = TaskData.from_action_item(action_item)

            if existing_sync:
                # Update existing task
                result = await integration.update_task(
                    existing_sync.external_id,
                    task_data
                )
            else:
                # Create new task
                result = await integration.create_task(task_data)

            if result.success:
                synced_count += 1

                if existing_sync:
                    existing_sync.last_synced_at = datetime.utcnow()
                    existing_sync.sync_errors = 0
                    existing_sync.last_error = None
                else:
                    sync_record = ActionItemSync(
                        action_item_id=action_item.id,
                        connection_id=connection.id,
                        external_id=result.external_id,
                        external_url=result.external_url,
                    )
                    db.add(sync_record)

                results.append({
                    "action_item_id": action_item.id,
                    "success": True,
                    "external_id": result.external_id,
                    "external_url": result.external_url,
                })
            else:
                failed_count += 1
                if existing_sync:
                    existing_sync.sync_errors += 1
                    existing_sync.last_error = result.error

                results.append({
                    "action_item_id": action_item.id,
                    "success": False,
                    "error": result.error,
                })

        # Update connection sync timestamp
        connection.last_sync_at = datetime.utcnow()
        if failed_count > 0:
            connection.error_count += failed_count
        db.commit()

    finally:
        await integration.close()

    return SyncResponse(
        success=failed_count == 0,
        synced_count=synced_count,
        failed_count=failed_count,
        results=results,
    )


@router.post("/{provider}/sync-all")
async def sync_all_pending_action_items(
    provider: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync all pending action items that haven't been synced yet.
    """
    if provider not in PM_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == provider,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    if not connection.project_id:
        raise HTTPException(status_code=400, detail="No project/database selected")

    # Get pending action items that haven't been synced
    synced_ids = db.query(ActionItemSync.action_item_id).filter(
        ActionItemSync.connection_id == connection.id
    ).subquery()

    pending_items = db.query(ActionItem).filter(
        ActionItem.user_id == current_user.id,
        ActionItem.status == "pending",
        ~ActionItem.id.in_(synced_ids)
    ).all()

    if not pending_items:
        return SyncResponse(
            success=True,
            synced_count=0,
            failed_count=0,
            results=[{"message": "No pending action items to sync"}],
        )

    # Use the regular sync endpoint
    request = BulkSyncRequest(action_item_ids=[item.id for item in pending_items])
    return await sync_action_items(provider, request, background_tasks, db, current_user)


@router.get("/{provider}/sync-status")
async def get_sync_status(
    provider: str,
    action_item_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the sync status of an action item with the specified provider.
    """
    if provider not in PM_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == provider,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    # Verify action item belongs to user
    action_item = db.query(ActionItem).filter(
        ActionItem.id == action_item_id,
        ActionItem.user_id == current_user.id
    ).first()

    if not action_item:
        raise HTTPException(status_code=404, detail="Action item not found")

    sync_record = db.query(ActionItemSync).filter(
        ActionItemSync.action_item_id == action_item_id,
        ActionItemSync.connection_id == connection.id
    ).first()

    if not sync_record:
        return {
            "synced": False,
            "action_item_id": action_item_id,
            "provider": provider,
        }

    # Optionally fetch current status from external system
    external_status = None
    try:
        integration = get_integration_instance(provider, connection, db)
        external_status = await integration.sync_status(sync_record.external_id)
        await integration.close()
    except Exception as e:
        logger.error(f"Error fetching external status: {e}")

    return {
        "synced": True,
        "action_item_id": action_item_id,
        "provider": provider,
        "external_id": sync_record.external_id,
        "external_url": sync_record.external_url,
        "external_status": external_status.value if external_status else None,
        "last_synced_at": sync_record.last_synced_at,
        "sync_errors": sync_record.sync_errors,
        "last_error": sync_record.last_error,
    }


# =============================================================================
# INTEGRATION SETTINGS
# =============================================================================

@router.put("/{provider}/settings")
async def update_integration_settings(
    provider: str,
    settings: PMIntegrationSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update settings for a project management integration."""
    if provider not in PM_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == provider,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    connection.auto_sync_enabled = settings.auto_sync_enabled
    connection.sync_completed_status = settings.sync_completed_status
    connection.sync_priority = settings.sync_priority
    if settings.default_labels is not None:
        connection.default_labels = settings.default_labels
    connection.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Settings updated"}


@router.get("/{provider}/settings")
async def get_integration_settings(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get settings for a project management integration."""
    if provider not in PM_PROVIDERS:
        raise HTTPException(status_code=400, detail="Invalid provider")

    connection = db.query(ProjectManagementConnection).filter(
        ProjectManagementConnection.user_id == current_user.id,
        ProjectManagementConnection.provider == provider,
        ProjectManagementConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail=f"{provider.title()} not connected")

    return PMIntegrationSettings(
        auto_sync_enabled=connection.auto_sync_enabled,
        sync_completed_status=connection.sync_completed_status,
        sync_priority=connection.sync_priority,
        default_labels=connection.default_labels or [],
    )
