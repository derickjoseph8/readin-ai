"""
Meeting lifecycle management service.

Handles:
- Meeting state machine (IDLE -> DETECTING -> ACTIVE -> PAUSED -> ENDED)
- Meeting creation and updates
- Session persistence
"""

import logging
from enum import Enum, auto
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class MeetingState(Enum):
    """Meeting lifecycle states."""
    IDLE = auto()        # No active meeting
    DETECTING = auto()   # Looking for meeting app
    ACTIVE = auto()      # Meeting in progress
    PAUSED = auto()      # Meeting paused (user muted/away)
    ENDED = auto()       # Meeting concluded


class MeetingEvent(Enum):
    """Events that trigger state transitions."""
    START_DETECTION = auto()
    MEETING_FOUND = auto()
    MEETING_LOST = auto()
    PAUSE = auto()
    RESUME = auto()
    END = auto()
    CANCEL = auto()


@dataclass
class MeetingContext:
    """Current meeting context and metadata."""
    meeting_id: Optional[int] = None
    meeting_type: str = "general"
    title: Optional[str] = None
    meeting_app: Optional[str] = None
    started_at: Optional[datetime] = None
    participant_count: int = 1
    conversation_count: int = 0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class MeetingService:
    """
    Service for managing meeting lifecycle.

    Uses a state machine pattern for clean state management.
    """

    # Valid state transitions
    TRANSITIONS = {
        MeetingState.IDLE: {
            MeetingEvent.START_DETECTION: MeetingState.DETECTING,
        },
        MeetingState.DETECTING: {
            MeetingEvent.MEETING_FOUND: MeetingState.ACTIVE,
            MeetingEvent.CANCEL: MeetingState.IDLE,
        },
        MeetingState.ACTIVE: {
            MeetingEvent.PAUSE: MeetingState.PAUSED,
            MeetingEvent.END: MeetingState.ENDED,
            MeetingEvent.MEETING_LOST: MeetingState.DETECTING,
        },
        MeetingState.PAUSED: {
            MeetingEvent.RESUME: MeetingState.ACTIVE,
            MeetingEvent.END: MeetingState.ENDED,
        },
        MeetingState.ENDED: {
            MeetingEvent.START_DETECTION: MeetingState.DETECTING,
        },
    }

    def __init__(self, api_client=None):
        """
        Initialize meeting service.

        Args:
            api_client: Backend API client for synchronization
        """
        self._state = MeetingState.IDLE
        self._context = MeetingContext()
        self._api_client = api_client
        self._listeners: Dict[str, list] = {
            "state_change": [],
            "meeting_start": [],
            "meeting_end": [],
            "error": [],
        }

    @property
    def state(self) -> MeetingState:
        """Get current meeting state."""
        return self._state

    @property
    def context(self) -> MeetingContext:
        """Get current meeting context."""
        return self._context

    @property
    def is_active(self) -> bool:
        """Check if a meeting is currently active."""
        return self._state == MeetingState.ACTIVE

    @property
    def is_in_meeting(self) -> bool:
        """Check if in any meeting-related state."""
        return self._state in (MeetingState.ACTIVE, MeetingState.PAUSED)

    def add_listener(self, event: str, callback: Callable):
        """Add event listener."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable):
        """Remove event listener."""
        if event in self._listeners and callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def _emit(self, event: str, *args, **kwargs):
        """Emit event to listeners."""
        for callback in self._listeners.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in listener for {event}: {e}")

    def transition(self, event: MeetingEvent) -> bool:
        """
        Attempt a state transition.

        Args:
            event: The event triggering the transition

        Returns:
            True if transition was successful
        """
        valid_transitions = self.TRANSITIONS.get(self._state, {})
        new_state = valid_transitions.get(event)

        if new_state is None:
            logger.warning(
                f"Invalid transition: {self._state.name} + {event.name}"
            )
            return False

        old_state = self._state
        self._state = new_state

        logger.info(f"Meeting state: {old_state.name} -> {new_state.name}")
        self._emit("state_change", old_state, new_state, event)

        return True

    async def start_meeting(
        self,
        meeting_type: str = "general",
        title: Optional[str] = None,
        meeting_app: Optional[str] = None,
        participant_count: int = 1,
    ) -> bool:
        """
        Start a new meeting session.

        Args:
            meeting_type: Type of meeting (interview, general, etc.)
            title: Optional meeting title
            meeting_app: Detected meeting application
            participant_count: Number of participants

        Returns:
            True if meeting started successfully
        """
        if not self.transition(MeetingEvent.MEETING_FOUND):
            return False

        # Update context
        self._context = MeetingContext(
            meeting_type=meeting_type,
            title=title,
            meeting_app=meeting_app,
            started_at=datetime.now(),
            participant_count=participant_count,
        )

        # Sync with backend
        if self._api_client:
            try:
                result = await self._api_client.start_meeting(
                    meeting_type=meeting_type,
                    title=title,
                    meeting_app=meeting_app,
                    participant_count=participant_count,
                )
                if result and "id" in result:
                    self._context.meeting_id = result["id"]
                    logger.info(f"Meeting synced with backend: {result['id']}")
            except Exception as e:
                logger.error(f"Failed to sync meeting start: {e}")
                # Continue anyway - we'll sync later

        self._emit("meeting_start", self._context)
        return True

    async def end_meeting(
        self,
        notes: str = "",
        generate_summary: bool = True,
        send_email: bool = False,
    ) -> bool:
        """
        End the current meeting.

        Args:
            notes: Optional meeting notes
            generate_summary: Whether to generate AI summary
            send_email: Whether to email the summary

        Returns:
            True if meeting ended successfully
        """
        if not self.transition(MeetingEvent.END):
            return False

        self._context.notes = notes

        # Sync with backend
        if self._api_client and self._context.meeting_id:
            try:
                await self._api_client.end_meeting(
                    meeting_id=self._context.meeting_id,
                    notes=notes,
                    generate_summary=generate_summary,
                    send_email=send_email,
                )
                logger.info(f"Meeting {self._context.meeting_id} ended")
            except Exception as e:
                logger.error(f"Failed to sync meeting end: {e}")

        self._emit("meeting_end", self._context)
        return True

    def pause(self) -> bool:
        """Pause the current meeting."""
        return self.transition(MeetingEvent.PAUSE)

    def resume(self) -> bool:
        """Resume a paused meeting."""
        return self.transition(MeetingEvent.RESUME)

    def start_detection(self) -> bool:
        """Start detecting meeting applications."""
        return self.transition(MeetingEvent.START_DETECTION)

    def cancel_detection(self) -> bool:
        """Cancel meeting detection."""
        return self.transition(MeetingEvent.CANCEL)

    def increment_conversations(self):
        """Increment conversation count."""
        self._context.conversation_count += 1

    def update_participant_count(self, count: int):
        """Update participant count."""
        self._context.participant_count = count

    def get_summary(self) -> Dict[str, Any]:
        """Get meeting summary data."""
        duration = None
        if self._context.started_at:
            duration = (datetime.now() - self._context.started_at).total_seconds()

        return {
            "meeting_id": self._context.meeting_id,
            "meeting_type": self._context.meeting_type,
            "title": self._context.title,
            "meeting_app": self._context.meeting_app,
            "started_at": self._context.started_at.isoformat() if self._context.started_at else None,
            "duration_seconds": int(duration) if duration else None,
            "conversation_count": self._context.conversation_count,
            "participant_count": self._context.participant_count,
            "state": self._state.name,
        }
