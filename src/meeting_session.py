"""Meeting Session Manager for tracking and syncing meeting data."""

import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
import threading

logger = logging.getLogger(__name__)


@dataclass
class ConversationExchange:
    """Single conversation exchange during a meeting."""
    heard_text: str
    response_text: str
    speaker: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    synced: bool = False


class MeetingSession:
    """Manages a meeting session with conversation tracking and backend sync."""

    # Meeting types
    MEETING_TYPES = [
        ("general", "General Meeting"),
        ("interview", "Job Interview"),
        ("manager", "Manager 1:1"),
        ("client", "Client Meeting"),
        ("sales", "Sales Call"),
        ("tv", "TV/Media Appearance"),
        ("presentation", "Presentation"),
        ("training", "Training Session"),
    ]

    def __init__(self, api_client):
        self.api = api_client
        self._meeting_id: Optional[int] = None
        self._meeting_type: str = "general"
        self._title: Optional[str] = None
        self._meeting_app: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._conversations: List[ConversationExchange] = []
        self._is_active: bool = False
        self._sync_lock = threading.Lock()
        self._on_session_change: Optional[Callable] = None

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def meeting_id(self) -> Optional[int]:
        return self._meeting_id

    @property
    def meeting_type(self) -> str:
        return self._meeting_type

    @property
    def conversation_count(self) -> int:
        return len(self._conversations)

    @property
    def duration_seconds(self) -> int:
        if not self._started_at:
            return 0
        return int((datetime.now() - self._started_at).total_seconds())

    def set_session_change_callback(self, callback: Callable):
        """Set callback for session state changes."""
        self._on_session_change = callback

    def _notify_change(self):
        """Notify listeners of session state change."""
        if self._on_session_change:
            try:
                self._on_session_change(self)
            except Exception as e:
                logger.error(f"Session change callback error: {e}")

    def start(self, meeting_type: str = "general", title: Optional[str] = None,
              meeting_app: Optional[str] = None) -> bool:
        """Start a new meeting session."""
        if self._is_active:
            return False

        self._meeting_type = meeting_type
        self._title = title
        self._meeting_app = meeting_app
        self._started_at = datetime.now()
        self._conversations = []
        self._is_active = True

        # Try to sync with backend
        if self.api.is_logged_in():
            result = self.api.start_meeting(
                meeting_type=meeting_type,
                title=title,
                meeting_app=meeting_app
            )
            if "id" in result:
                self._meeting_id = result["id"]

        self._notify_change()
        return True

    def end(self) -> Optional[Dict]:
        """End the current meeting session and get summary."""
        if not self._is_active:
            return None

        self._is_active = False
        summary = None

        # Sync any pending conversations
        self._sync_conversations()

        # End meeting on backend and get summary
        if self._meeting_id and self.api.is_logged_in():
            result = self.api.end_meeting(self._meeting_id)
            if "summary" in result:
                summary = result

        self._notify_change()
        return summary

    def add_conversation(self, heard_text: str, response_text: str,
                         speaker: Optional[str] = None) -> None:
        """Add a conversation exchange to the session."""
        exchange = ConversationExchange(
            heard_text=heard_text,
            response_text=response_text,
            speaker=speaker
        )
        self._conversations.append(exchange)

        # Try to sync immediately in background
        if self._meeting_id and self.api.is_logged_in():
            threading.Thread(target=self._sync_single_conversation, args=(exchange,), daemon=True).start()

    def _sync_single_conversation(self, exchange: ConversationExchange) -> None:
        """Sync a single conversation to backend."""
        with self._sync_lock:
            if exchange.synced:
                return
            try:
                result = self.api.save_conversation(
                    meeting_id=self._meeting_id,
                    heard_text=exchange.heard_text,
                    response_text=exchange.response_text,
                    speaker=exchange.speaker
                )
                if "error" not in result:
                    exchange.synced = True
            except Exception as e:
                logger.error(f"Failed to sync conversation: {e}")

    def _sync_conversations(self) -> None:
        """Sync all unsynced conversations to backend."""
        if not self._meeting_id or not self.api.is_logged_in():
            return

        with self._sync_lock:
            for exchange in self._conversations:
                if not exchange.synced:
                    try:
                        result = self.api.save_conversation(
                            meeting_id=self._meeting_id,
                            heard_text=exchange.heard_text,
                            response_text=exchange.response_text,
                            speaker=exchange.speaker
                        )
                        if "error" not in result:
                            exchange.synced = True
                    except Exception as e:
                        logger.error(f"Failed to sync conversation: {e}")

    def get_summary(self) -> Optional[Dict]:
        """Get summary for current or last meeting."""
        if self._meeting_id and self.api.is_logged_in():
            return self.api.get_meeting_summary(self._meeting_id)
        return None

    def get_briefing(self, participant_names: List[str] = None,
                     meeting_context: Optional[str] = None) -> Optional[Dict]:
        """Get pre-meeting briefing."""
        if not self.api.is_logged_in():
            return None

        return self.api.generate_briefing(
            participant_names=participant_names,
            meeting_context=meeting_context,
            meeting_type=self._meeting_type
        )

    def get_conversations(self) -> List[Dict]:
        """Get all conversations as dictionaries."""
        return [
            {
                "heard_text": c.heard_text,
                "response_text": c.response_text,
                "speaker": c.speaker,
                "timestamp": c.timestamp.isoformat(),
                "synced": c.synced
            }
            for c in self._conversations
        ]

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        return {
            "is_active": self._is_active,
            "meeting_id": self._meeting_id,
            "meeting_type": self._meeting_type,
            "title": self._title,
            "meeting_app": self._meeting_app,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "duration_seconds": self.duration_seconds,
            "conversation_count": len(self._conversations),
            "synced_count": sum(1 for c in self._conversations if c.synced)
        }

    def resume_active(self) -> bool:
        """Try to resume an active meeting from the backend."""
        if not self.api.is_logged_in():
            return False

        active = self.api.get_active_meeting()
        if active and "id" in active:
            self._meeting_id = active["id"]
            self._meeting_type = active.get("meeting_type", "general")
            self._title = active.get("title")
            self._meeting_app = active.get("meeting_app")
            self._started_at = datetime.fromisoformat(active["started_at"]) if active.get("started_at") else datetime.now()
            self._is_active = True
            self._notify_change()
            return True
        return False

    def reset(self) -> None:
        """Reset session state."""
        self._meeting_id = None
        self._meeting_type = "general"
        self._title = None
        self._meeting_app = None
        self._started_at = None
        self._conversations = []
        self._is_active = False
        self._notify_change()
