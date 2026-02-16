"""
Centralized state management for ReadIn AI Desktop App.

Provides:
- Application state singleton
- Meeting state machine
- Observable state changes
"""

from .app_state import AppState, get_app_state
from .meeting_state import MeetingStateMachine, MeetingState

__all__ = [
    "AppState",
    "get_app_state",
    "MeetingStateMachine",
    "MeetingState",
]
