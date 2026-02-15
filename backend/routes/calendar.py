"""
Calendar API routes.

Provides endpoints for calendar integration with
Google Calendar and Microsoft Outlook.
"""

import secrets
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User, CalendarIntegration
from auth import get_current_user
from services.calendar_service import calendar_service, CalendarEvent

router = APIRouter(prefix="/calendar", tags=["Calendar"])


class CalendarProviderResponse(BaseModel):
    """Available calendar providers response."""
    providers: List[str]


class CalendarAuthUrlResponse(BaseModel):
    """Calendar auth URL response."""
    auth_url: str
    state: str


class CalendarEventResponse(BaseModel):
    """Calendar event response."""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    meeting_link: Optional[str]
    provider: str


class CalendarEventsResponse(BaseModel):
    """Calendar events list response."""
    events: List[CalendarEventResponse]
    count: int


class CreateEventRequest(BaseModel):
    """Create calendar event request."""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    attendees: Optional[List[str]] = None


class CalendarIntegrationResponse(BaseModel):
    """Calendar integration status response."""
    provider: str
    connected: bool
    email: Optional[str]
    connected_at: Optional[datetime]


@router.get("/providers", response_model=CalendarProviderResponse)
def get_calendar_providers():
    """Get list of available calendar providers."""
    return CalendarProviderResponse(
        providers=calendar_service.get_available_providers()
    )


@router.get("/integrations")
def get_calendar_integrations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's calendar integrations."""
    integrations = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == user.id
    ).all()

    return [
        CalendarIntegrationResponse(
            provider=i.provider,
            connected=i.is_active,
            email=i.calendar_email,
            connected_at=i.connected_at
        )
        for i in integrations
    ]


@router.get("/auth/{provider}", response_model=CalendarAuthUrlResponse)
def get_calendar_auth_url(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get OAuth authorization URL for a calendar provider.

    Supported providers: google, microsoft
    """
    if provider not in calendar_service.get_available_providers():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Calendar provider '{provider}' is not available or not configured"
        )

    # Generate state token
    state = secrets.token_urlsafe(32)

    # Store state in user's session or database
    # For simplicity, we'll include user_id in state
    state_data = f"{user.id}:{state}"

    try:
        auth_url = calendar_service.get_auth_url(provider, state_data)
        return CalendarAuthUrlResponse(auth_url=auth_url, state=state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}"
        )


@router.get("/{provider}/callback")
def calendar_oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    OAuth callback endpoint for calendar providers.

    This endpoint is called by the OAuth provider after user authorization.
    """
    # Parse state to get user_id
    try:
        user_id_str, _ = state.split(':', 1)
        user_id = int(user_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Exchange code for tokens
    try:
        tokens = calendar_service.exchange_code(provider, code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code: {str(e)}"
        )

    # Store or update integration
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == user.id,
        CalendarIntegration.provider == provider
    ).first()

    if integration:
        integration.access_token = tokens['access_token']
        integration.refresh_token = tokens.get('refresh_token')
        integration.is_active = True
        integration.connected_at = datetime.utcnow()
    else:
        integration = CalendarIntegration(
            user_id=user.id,
            provider=provider,
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            is_active=True,
            connected_at=datetime.utcnow()
        )
        db.add(integration)

    db.commit()

    # Redirect to success page
    return {"status": "success", "message": f"{provider.title()} Calendar connected successfully"}


@router.delete("/{provider}")
def disconnect_calendar(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a calendar integration."""
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == user.id,
        CalendarIntegration.provider == provider
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} calendar integration found"
        )

    db.delete(integration)
    db.commit()

    return {"status": "success", "message": f"{provider.title()} Calendar disconnected"}


@router.get("/{provider}/events", response_model=CalendarEventsResponse)
def get_calendar_events(
    provider: str,
    max_results: int = Query(default=10, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upcoming calendar events from a connected provider.
    """
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == user.id,
        CalendarIntegration.provider == provider,
        CalendarIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {provider} calendar integration found"
        )

    credentials_data = {
        'access_token': integration.access_token,
        'refresh_token': integration.refresh_token,
    }

    try:
        events = calendar_service.get_upcoming_events(
            provider,
            credentials_data,
            max_results
        )

        return CalendarEventsResponse(
            events=[
                CalendarEventResponse(
                    id=e.id,
                    title=e.title,
                    description=e.description,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    location=e.location,
                    attendees=e.attendees,
                    meeting_link=e.meeting_link,
                    provider=e.provider
                )
                for e in events
            ],
            count=len(events)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )


@router.post("/{provider}/events", response_model=CalendarEventResponse)
def create_calendar_event(
    provider: str,
    request: CreateEventRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new calendar event.
    """
    integration = db.query(CalendarIntegration).filter(
        CalendarIntegration.user_id == user.id,
        CalendarIntegration.provider == provider,
        CalendarIntegration.is_active == True
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {provider} calendar integration found"
        )

    credentials_data = {
        'access_token': integration.access_token,
        'refresh_token': integration.refresh_token,
    }

    try:
        if provider == 'google':
            event = calendar_service.google.create_event(
                credentials_data,
                request.title,
                request.start_time,
                request.end_time,
                request.description,
                request.attendees
            )
        elif provider == 'microsoft':
            event = calendar_service.microsoft.create_event(
                credentials_data,
                request.title,
                request.start_time,
                request.end_time,
                request.description,
                request.attendees
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {provider}"
            )

        return CalendarEventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            attendees=event.attendees,
            meeting_link=event.meeting_link,
            provider=event.provider
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )
