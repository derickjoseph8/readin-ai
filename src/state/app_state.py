"""
Centralized application state management.

Single source of truth for application state.
"""

import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Backend connection status."""
    CONNECTED = auto()
    DISCONNECTED = auto()
    CONNECTING = auto()
    ERROR = auto()


class SubscriptionStatus(Enum):
    """User subscription status."""
    TRIAL = auto()
    ACTIVE = auto()
    EXPIRED = auto()
    CANCELLED = auto()


@dataclass
class UserState:
    """User state information."""
    is_logged_in: bool = False
    user_id: Optional[int] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    profession: Optional[str] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.TRIAL
    trial_days_remaining: int = 0
    daily_usage: int = 0
    daily_limit: Optional[int] = None


@dataclass
class MeetingStateData:
    """Meeting state information."""
    is_active: bool = False
    meeting_id: Optional[int] = None
    meeting_type: str = "general"
    title: Optional[str] = None
    meeting_app: Optional[str] = None
    started_at: Optional[datetime] = None
    conversation_count: int = 0
    participant_count: int = 1


@dataclass
class AudioState:
    """Audio capture state."""
    is_capturing: bool = False
    selected_device: Optional[str] = None
    audio_level: float = 0.0
    is_muted: bool = False


@dataclass
class UIState:
    """UI state information."""
    is_overlay_visible: bool = False
    overlay_position: tuple = (100, 100)
    overlay_size: tuple = (400, 300)
    theme: str = "dark"
    font_size: int = 14
    opacity: float = 0.95


class AppState:
    """
    Centralized application state singleton.

    Manages all application state and notifies observers of changes.
    """

    _instance: Optional['AppState'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize state."""
        self._user = UserState()
        self._meeting = MeetingStateData()
        self._audio = AudioState()
        self._ui = UIState()
        self._connection = ConnectionStatus.DISCONNECTED
        self._observers: Dict[str, List[Callable]] = {}
        self._last_error: Optional[str] = None
        self._initialized = True

    # Properties
    @property
    def user(self) -> UserState:
        return self._user

    @property
    def meeting(self) -> MeetingStateData:
        return self._meeting

    @property
    def audio(self) -> AudioState:
        return self._audio

    @property
    def ui(self) -> UIState:
        return self._ui

    @property
    def connection(self) -> ConnectionStatus:
        return self._connection

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    # Observer pattern
    def subscribe(self, event: str, callback: Callable):
        """Subscribe to state changes."""
        if event not in self._observers:
            self._observers[event] = []
        self._observers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        """Unsubscribe from state changes."""
        if event in self._observers and callback in self._observers[event]:
            self._observers[event].remove(callback)

    def _notify(self, event: str, *args, **kwargs):
        """Notify observers of state change."""
        for callback in self._observers.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Observer error for {event}: {e}")

        # Also notify generic "state_changed" observers
        for callback in self._observers.get("state_changed", []):
            try:
                callback(event, *args, **kwargs)
            except Exception as e:
                logger.error(f"State change observer error: {e}")

    # User state updates
    def set_logged_in(
        self,
        user_id: int,
        email: str,
        full_name: str = None,
        profession: str = None
    ):
        """Set user as logged in."""
        self._user.is_logged_in = True
        self._user.user_id = user_id
        self._user.email = email
        self._user.full_name = full_name
        self._user.profession = profession
        self._notify("user_login", self._user)

    def set_logged_out(self):
        """Set user as logged out."""
        self._user = UserState()
        self._notify("user_logout")

    def update_subscription(
        self,
        status: SubscriptionStatus,
        trial_days: int = 0,
        daily_usage: int = 0,
        daily_limit: int = None
    ):
        """Update subscription status."""
        self._user.subscription_status = status
        self._user.trial_days_remaining = trial_days
        self._user.daily_usage = daily_usage
        self._user.daily_limit = daily_limit
        self._notify("subscription_update", self._user)

    # Meeting state updates
    def start_meeting(
        self,
        meeting_id: int,
        meeting_type: str = "general",
        title: str = None,
        meeting_app: str = None
    ):
        """Start a meeting."""
        self._meeting.is_active = True
        self._meeting.meeting_id = meeting_id
        self._meeting.meeting_type = meeting_type
        self._meeting.title = title
        self._meeting.meeting_app = meeting_app
        self._meeting.started_at = datetime.now()
        self._meeting.conversation_count = 0
        self._notify("meeting_start", self._meeting)

    def end_meeting(self):
        """End the current meeting."""
        old_meeting = self._meeting
        self._meeting = MeetingStateData()
        self._notify("meeting_end", old_meeting)

    def increment_conversations(self):
        """Increment conversation count."""
        self._meeting.conversation_count += 1
        self._notify("conversation_added", self._meeting.conversation_count)

    # Audio state updates
    def set_audio_capturing(self, is_capturing: bool, device: str = None):
        """Update audio capture state."""
        self._audio.is_capturing = is_capturing
        if device:
            self._audio.selected_device = device
        self._notify("audio_state", self._audio)

    def set_audio_level(self, level: float):
        """Update audio level (0.0 - 1.0)."""
        self._audio.audio_level = max(0.0, min(1.0, level))
        self._notify("audio_level", self._audio.audio_level)

    def set_muted(self, is_muted: bool):
        """Set mute state."""
        self._audio.is_muted = is_muted
        self._notify("mute_state", is_muted)

    # UI state updates
    def set_overlay_visible(self, visible: bool):
        """Set overlay visibility."""
        self._ui.is_overlay_visible = visible
        self._notify("overlay_visibility", visible)

    def set_overlay_position(self, x: int, y: int):
        """Set overlay position."""
        self._ui.overlay_position = (x, y)
        self._notify("overlay_position", (x, y))

    def set_theme(self, theme: str):
        """Set UI theme."""
        self._ui.theme = theme
        self._notify("theme_change", theme)

    # Connection state
    def set_connection_status(self, status: ConnectionStatus):
        """Update connection status."""
        old_status = self._connection
        self._connection = status
        self._notify("connection_change", status, old_status)

    # Error handling
    def set_error(self, error: str):
        """Set last error."""
        self._last_error = error
        self._notify("error", error)

    def clear_error(self):
        """Clear last error."""
        self._last_error = None

    # Serialization
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "user": {
                "is_logged_in": self._user.is_logged_in,
                "user_id": self._user.user_id,
                "email": self._user.email,
                "subscription": self._user.subscription_status.name,
            },
            "meeting": {
                "is_active": self._meeting.is_active,
                "meeting_id": self._meeting.meeting_id,
                "meeting_type": self._meeting.meeting_type,
                "conversation_count": self._meeting.conversation_count,
            },
            "audio": {
                "is_capturing": self._audio.is_capturing,
                "is_muted": self._audio.is_muted,
            },
            "connection": self._connection.name,
        }


# Global state accessor
def get_app_state() -> AppState:
    """Get the global application state instance."""
    return AppState()
