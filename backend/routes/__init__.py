"""API Routes for ReadIn AI."""

from .professions import router as professions_router
from .organizations import router as organizations_router
from .meetings import router as meetings_router
from .conversations import router as conversations_router
from .tasks import router as tasks_router
from .briefings import router as briefings_router
from .interviews import router as interviews_router

__all__ = [
    "professions_router",
    "organizations_router",
    "meetings_router",
    "conversations_router",
    "tasks_router",
    "briefings_router",
    "interviews_router",
]
