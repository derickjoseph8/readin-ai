"""
Calendar Integration Service

Provides integration with Google Calendar and Microsoft Outlook
for syncing meetings and action items.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import json

# Google Calendar imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Microsoft Graph imports
try:
    import msal
    import requests
    MICROSOFT_AVAILABLE = True
except ImportError:
    MICROSOFT_AVAILABLE = False


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[str]
    meeting_link: Optional[str]
    provider: str  # 'google' or 'microsoft'


class GoogleCalendarService:
    """Google Calendar integration service."""

    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
    ]

    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/v1/calendar/google/callback')

    def is_configured(self) -> bool:
        """Check if Google Calendar is configured."""
        return bool(self.client_id and self.client_secret and GOOGLE_AVAILABLE)

    def get_auth_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        if not self.is_configured():
            raise ValueError("Google Calendar not configured")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        flow.state = state

        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        if not self.is_configured():
            raise ValueError("Google Calendar not configured")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes),
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }

    def get_upcoming_events(
        self,
        credentials_data: Dict[str, Any],
        max_results: int = 10,
        time_min: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Get upcoming calendar events."""
        if not GOOGLE_AVAILABLE:
            return []

        credentials = Credentials(
            token=credentials_data['access_token'],
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=credentials_data.get('client_id', self.client_id),
            client_secret=credentials_data.get('client_secret', self.client_secret),
            scopes=credentials_data.get('scopes', self.SCOPES)
        )

        service = build('calendar', 'v3', credentials=credentials)

        if time_min is None:
            time_min = datetime.utcnow()

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() + 'Z',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = []
        for event in events_result.get('items', []):
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            # Parse attendees
            attendees = [a.get('email', '') for a in event.get('attendees', [])]

            # Extract meeting link
            meeting_link = None
            if 'conferenceData' in event:
                for entry_point in event['conferenceData'].get('entryPoints', []):
                    if entry_point.get('entryPointType') == 'video':
                        meeting_link = entry_point.get('uri')
                        break

            events.append(CalendarEvent(
                id=event['id'],
                title=event.get('summary', 'No Title'),
                description=event.get('description'),
                start_time=datetime.fromisoformat(start.replace('Z', '+00:00')),
                end_time=datetime.fromisoformat(end.replace('Z', '+00:00')),
                location=event.get('location'),
                attendees=attendees,
                meeting_link=meeting_link,
                provider='google'
            ))

        return events

    def create_event(
        self,
        credentials_data: Dict[str, Any],
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> CalendarEvent:
        """Create a new calendar event."""
        if not GOOGLE_AVAILABLE:
            raise ValueError("Google Calendar not available")

        credentials = Credentials(
            token=credentials_data['access_token'],
            refresh_token=credentials_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.SCOPES
        )

        service = build('calendar', 'v3', credentials=credentials)

        event_body = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]

        event = service.events().insert(calendarId='primary', body=event_body).execute()

        return CalendarEvent(
            id=event['id'],
            title=event.get('summary', title),
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=None,
            attendees=attendees or [],
            meeting_link=None,
            provider='google'
        )


class MicrosoftCalendarService:
    """Microsoft Outlook Calendar integration service."""

    SCOPES = ['Calendars.ReadWrite', 'User.Read']
    AUTHORITY = 'https://login.microsoftonline.com/common'
    GRAPH_URL = 'https://graph.microsoft.com/v1.0'

    def __init__(self):
        self.client_id = os.getenv('MICROSOFT_CLIENT_ID')
        self.client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        self.redirect_uri = os.getenv('MICROSOFT_REDIRECT_URI', 'http://localhost:8000/api/v1/calendar/microsoft/callback')

    def is_configured(self) -> bool:
        """Check if Microsoft Calendar is configured."""
        return bool(self.client_id and self.client_secret and MICROSOFT_AVAILABLE)

    def get_auth_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        if not self.is_configured():
            raise ValueError("Microsoft Calendar not configured")

        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.AUTHORITY,
            client_credential=self.client_secret
        )

        auth_url = app.get_authorization_request_url(
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri,
            state=state
        )

        return auth_url

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        if not self.is_configured():
            raise ValueError("Microsoft Calendar not configured")

        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.AUTHORITY,
            client_credential=self.client_secret
        )

        result = app.acquire_token_by_authorization_code(
            code,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )

        if 'error' in result:
            raise ValueError(f"Token exchange failed: {result.get('error_description', result.get('error'))}")

        return {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token'),
            'expires_in': result.get('expires_in'),
            'token_type': result.get('token_type'),
        }

    def get_upcoming_events(
        self,
        credentials_data: Dict[str, Any],
        max_results: int = 10,
        time_min: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        """Get upcoming calendar events."""
        if not MICROSOFT_AVAILABLE:
            return []

        headers = {
            'Authorization': f"Bearer {credentials_data['access_token']}",
            'Content-Type': 'application/json'
        }

        if time_min is None:
            time_min = datetime.utcnow()

        params = {
            '$top': max_results,
            '$orderby': 'start/dateTime',
            '$filter': f"start/dateTime ge '{time_min.isoformat()}Z'"
        }

        response = requests.get(
            f"{self.GRAPH_URL}/me/events",
            headers=headers,
            params=params
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to fetch events: {response.text}")

        data = response.json()
        events = []

        for event in data.get('value', []):
            attendees = [a.get('emailAddress', {}).get('address', '') for a in event.get('attendees', [])]

            # Extract meeting link
            meeting_link = None
            if event.get('onlineMeeting'):
                meeting_link = event['onlineMeeting'].get('joinUrl')

            events.append(CalendarEvent(
                id=event['id'],
                title=event.get('subject', 'No Title'),
                description=event.get('body', {}).get('content'),
                start_time=datetime.fromisoformat(event['start']['dateTime']),
                end_time=datetime.fromisoformat(event['end']['dateTime']),
                location=event.get('location', {}).get('displayName'),
                attendees=attendees,
                meeting_link=meeting_link,
                provider='microsoft'
            ))

        return events

    def create_event(
        self,
        credentials_data: Dict[str, Any],
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None
    ) -> CalendarEvent:
        """Create a new calendar event."""
        if not MICROSOFT_AVAILABLE:
            raise ValueError("Microsoft Calendar not available")

        headers = {
            'Authorization': f"Bearer {credentials_data['access_token']}",
            'Content-Type': 'application/json'
        }

        event_body = {
            'subject': title,
            'body': {
                'contentType': 'HTML',
                'content': description or ''
            },
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC'
            }
        }

        if attendees:
            event_body['attendees'] = [
                {'emailAddress': {'address': email}, 'type': 'required'}
                for email in attendees
            ]

        response = requests.post(
            f"{self.GRAPH_URL}/me/events",
            headers=headers,
            json=event_body
        )

        if response.status_code not in (200, 201):
            raise ValueError(f"Failed to create event: {response.text}")

        event = response.json()

        return CalendarEvent(
            id=event['id'],
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=None,
            attendees=attendees or [],
            meeting_link=None,
            provider='microsoft'
        )


class CalendarService:
    """Unified calendar service for both Google and Microsoft."""

    def __init__(self):
        self.google = GoogleCalendarService()
        self.microsoft = MicrosoftCalendarService()

    def get_available_providers(self) -> List[str]:
        """Get list of configured calendar providers."""
        providers = []
        if self.google.is_configured():
            providers.append('google')
        if self.microsoft.is_configured():
            providers.append('microsoft')
        return providers

    def get_auth_url(self, provider: str, state: str) -> str:
        """Get OAuth URL for the specified provider."""
        if provider == 'google':
            return self.google.get_auth_url(state)
        elif provider == 'microsoft':
            return self.microsoft.get_auth_url(state)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def exchange_code(self, provider: str, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        if provider == 'google':
            return self.google.exchange_code(code)
        elif provider == 'microsoft':
            return self.microsoft.exchange_code(code)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_upcoming_events(
        self,
        provider: str,
        credentials_data: Dict[str, Any],
        max_results: int = 10
    ) -> List[CalendarEvent]:
        """Get upcoming events from the specified provider."""
        if provider == 'google':
            return self.google.get_upcoming_events(credentials_data, max_results)
        elif provider == 'microsoft':
            return self.microsoft.get_upcoming_events(credentials_data, max_results)
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Global instance
calendar_service = CalendarService()
