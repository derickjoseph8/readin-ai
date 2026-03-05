"""Integrations routes package."""

from .pm_integrations import router as pm_integrations_router

# Export as 'router' for main.py compatibility
router = pm_integrations_router

__all__ = ["pm_integrations_router", "router"]
