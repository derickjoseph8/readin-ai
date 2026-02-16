"""Admin routes for ReadIn AI e-commerce dashboard."""

from .dashboard import router as dashboard_router
from .teams import router as teams_router
from .tickets import router as tickets_router
from .chat import router as chat_router

__all__ = [
    "dashboard_router",
    "teams_router",
    "tickets_router",
    "chat_router",
]
