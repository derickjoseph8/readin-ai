"""
Meeting state machine implementation.

Provides formal state machine for meeting lifecycle management.
"""

import logging
from enum import Enum, auto
from typing import Optional, Callable, Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MeetingState(Enum):
    """Meeting lifecycle states."""
    IDLE = auto()           # No meeting
    DETECTING = auto()      # Looking for meeting app
    CONNECTING = auto()     # Connecting to backend
    ACTIVE = auto()         # Meeting in progress
    PAUSED = auto()         # Meeting paused
    ENDING = auto()         # Meeting ending (syncing)
    ENDED = auto()          # Meeting concluded
    ERROR = auto()          # Error state


class MeetingEvent(Enum):
    """Events that trigger state transitions."""
    START_DETECTION = auto()
    APP_DETECTED = auto()
    APP_LOST = auto()
    BACKEND_CONNECTED = auto()
    BACKEND_ERROR = auto()
    USER_START = auto()
    USER_PAUSE = auto()
    USER_RESUME = auto()
    USER_END = auto()
    SYNC_COMPLETE = auto()
    SYNC_ERROR = auto()
    RESET = auto()


class MeetingStateMachine:
    """
    Formal state machine for meeting lifecycle.

    Enforces valid state transitions and manages side effects.
    """

    # State transition table
    # Format: (current_state, event) -> (new_state, action_name)
    TRANSITIONS: Dict[tuple, tuple] = {
        # From IDLE
        (MeetingState.IDLE, MeetingEvent.START_DETECTION): (MeetingState.DETECTING, "on_start_detection"),

        # From DETECTING
        (MeetingState.DETECTING, MeetingEvent.APP_DETECTED): (MeetingState.CONNECTING, "on_app_detected"),
        (MeetingState.DETECTING, MeetingEvent.RESET): (MeetingState.IDLE, "on_reset"),

        # From CONNECTING
        (MeetingState.CONNECTING, MeetingEvent.BACKEND_CONNECTED): (MeetingState.ACTIVE, "on_meeting_start"),
        (MeetingState.CONNECTING, MeetingEvent.BACKEND_ERROR): (MeetingState.ERROR, "on_connection_error"),
        (MeetingState.CONNECTING, MeetingEvent.USER_START): (MeetingState.ACTIVE, "on_meeting_start"),

        # From ACTIVE
        (MeetingState.ACTIVE, MeetingEvent.USER_PAUSE): (MeetingState.PAUSED, "on_pause"),
        (MeetingState.ACTIVE, MeetingEvent.USER_END): (MeetingState.ENDING, "on_ending"),
        (MeetingState.ACTIVE, MeetingEvent.APP_LOST): (MeetingState.PAUSED, "on_app_lost"),

        # From PAUSED
        (MeetingState.PAUSED, MeetingEvent.USER_RESUME): (MeetingState.ACTIVE, "on_resume"),
        (MeetingState.PAUSED, MeetingEvent.USER_END): (MeetingState.ENDING, "on_ending"),
        (MeetingState.PAUSED, MeetingEvent.APP_DETECTED): (MeetingState.ACTIVE, "on_app_redetected"),

        # From ENDING
        (MeetingState.ENDING, MeetingEvent.SYNC_COMPLETE): (MeetingState.ENDED, "on_sync_complete"),
        (MeetingState.ENDING, MeetingEvent.SYNC_ERROR): (MeetingState.ENDED, "on_sync_error"),

        # From ENDED
        (MeetingState.ENDED, MeetingEvent.START_DETECTION): (MeetingState.DETECTING, "on_start_detection"),
        (MeetingState.ENDED, MeetingEvent.RESET): (MeetingState.IDLE, "on_reset"),

        # From ERROR
        (MeetingState.ERROR, MeetingEvent.RESET): (MeetingState.IDLE, "on_reset"),
        (MeetingState.ERROR, MeetingEvent.START_DETECTION): (MeetingState.DETECTING, "on_start_detection"),
    }

    def __init__(self):
        """Initialize state machine."""
        self._state = MeetingState.IDLE
        self._previous_state: Optional[MeetingState] = None
        self._context: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable]] = {
            "state_change": [],
            "transition_blocked": [],
        }
        self._transition_history: List[Dict] = []
        self._max_history = 50

    @property
    def state(self) -> MeetingState:
        """Get current state."""
        return self._state

    @property
    def previous_state(self) -> Optional[MeetingState]:
        """Get previous state."""
        return self._previous_state

    @property
    def context(self) -> Dict[str, Any]:
        """Get state context data."""
        return self._context

    @property
    def is_in_meeting(self) -> bool:
        """Check if in any meeting-related state."""
        return self._state in (
            MeetingState.ACTIVE,
            MeetingState.PAUSED,
            MeetingState.ENDING,
        )

    @property
    def can_start(self) -> bool:
        """Check if can start detection."""
        return self._state in (MeetingState.IDLE, MeetingState.ENDED, MeetingState.ERROR)

    def add_listener(self, event: str, callback: Callable):
        """Add event listener."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable):
        """Remove event listener."""
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def _notify(self, event: str, *args, **kwargs):
        """Notify listeners."""
        for callback in self._listeners.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Listener error for {event}: {e}")

    def can_transition(self, event: MeetingEvent) -> bool:
        """Check if transition is valid."""
        return (self._state, event) in self.TRANSITIONS

    def transition(self, event: MeetingEvent, **context) -> bool:
        """
        Attempt a state transition.

        Args:
            event: The triggering event
            **context: Additional context data

        Returns:
            True if transition was successful
        """
        transition_key = (self._state, event)

        if transition_key not in self.TRANSITIONS:
            logger.warning(
                f"Blocked transition: {self._state.name} + {event.name}"
            )
            self._notify("transition_blocked", self._state, event)
            return False

        new_state, action_name = self.TRANSITIONS[transition_key]
        old_state = self._state

        # Update state
        self._previous_state = old_state
        self._state = new_state

        # Update context
        self._context.update(context)
        self._context["last_transition"] = datetime.now().isoformat()

        # Record history
        self._transition_history.append({
            "from": old_state.name,
            "to": new_state.name,
            "event": event.name,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._transition_history) > self._max_history:
            self._transition_history = self._transition_history[-self._max_history:]

        logger.info(f"State transition: {old_state.name} -> {new_state.name} ({event.name})")

        # Execute action
        action = getattr(self, action_name, None)
        if action:
            try:
                action(**context)
            except Exception as e:
                logger.error(f"Action error in {action_name}: {e}")

        # Notify listeners
        self._notify("state_change", old_state, new_state, event, context)

        return True

    # State actions (side effects)
    def on_start_detection(self, **context):
        """Handle start detection."""
        self._context["detection_started"] = datetime.now().isoformat()

    def on_app_detected(self, app_name: str = None, **context):
        """Handle app detection."""
        self._context["detected_app"] = app_name

    def on_meeting_start(self, meeting_id: int = None, **context):
        """Handle meeting start."""
        self._context["meeting_id"] = meeting_id
        self._context["meeting_started"] = datetime.now().isoformat()
        self._context["conversation_count"] = 0

    def on_pause(self, **context):
        """Handle pause."""
        self._context["paused_at"] = datetime.now().isoformat()

    def on_resume(self, **context):
        """Handle resume."""
        if "paused_at" in self._context:
            del self._context["paused_at"]

    def on_app_lost(self, **context):
        """Handle app lost during meeting."""
        self._context["app_lost_at"] = datetime.now().isoformat()

    def on_app_redetected(self, **context):
        """Handle app redetection."""
        if "app_lost_at" in self._context:
            del self._context["app_lost_at"]

    def on_ending(self, **context):
        """Handle meeting ending."""
        self._context["ending_started"] = datetime.now().isoformat()

    def on_sync_complete(self, **context):
        """Handle sync completion."""
        self._context["sync_completed"] = datetime.now().isoformat()

    def on_sync_error(self, error: str = None, **context):
        """Handle sync error."""
        self._context["sync_error"] = error

    def on_connection_error(self, error: str = None, **context):
        """Handle connection error."""
        self._context["connection_error"] = error

    def on_reset(self, **context):
        """Handle reset."""
        self._context = {}

    def get_history(self) -> List[Dict]:
        """Get transition history."""
        return self._transition_history.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "state": self._state.name,
            "previous_state": self._previous_state.name if self._previous_state else None,
            "is_in_meeting": self.is_in_meeting,
            "can_start": self.can_start,
            "context": self._context.copy(),
        }
