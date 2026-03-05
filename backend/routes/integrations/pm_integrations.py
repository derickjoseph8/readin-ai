"""Project Management Integrations - Asana, Notion, Jira, Linear."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from routes.auth import get_current_user
from models import User
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/integrations", tags=["integrations"])

class ConnectRequest(BaseModel):
    access_token: Optional[str] = None
    domain: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    project_id: Optional[str] = None
    team_id: Optional[str] = None

# Asana
@router.post("/asana/connect")
async def connect_asana(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.integrations.asana_integration import AsanaIntegration
    client = AsanaIntegration(request.access_token)
    user = await client.get_user()
    return {"connected": True, "user": user}

@router.get("/asana/workspaces")
async def asana_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"workspaces": []}

@router.post("/asana/sync")
async def sync_asana(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"synced": True, "items": []}

# Notion
@router.post("/notion/connect")
async def connect_notion(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.integrations.notion_integration import NotionIntegration
    client = NotionIntegration(request.access_token)
    databases = await client.search_databases()
    return {"connected": True, "databases": databases}

@router.get("/notion/databases")
async def notion_databases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"databases": []}

@router.post("/notion/sync")
async def sync_notion(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"synced": True}

# Jira
@router.post("/jira/connect")
async def connect_jira(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.integrations.jira_integration import JiraIntegration
    client = JiraIntegration(request.domain, request.email, request.api_token)
    projects = await client.get_projects()
    return {"connected": True, "projects": projects}

@router.get("/jira/projects")
async def jira_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"projects": []}

@router.post("/jira/sync")
async def sync_jira(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"synced": True, "items": []}

# Linear
@router.post("/linear/connect")
async def connect_linear(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from services.integrations.linear_integration import LinearIntegration
    client = LinearIntegration(request.access_token)
    viewer = await client.get_viewer()
    return {"connected": True, "user": viewer}

@router.get("/linear/teams")
async def linear_teams(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"teams": []}

@router.post("/linear/sync")
async def sync_linear(request: ConnectRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"synced": True, "items": []}
