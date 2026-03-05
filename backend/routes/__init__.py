"""API Routes for ReadIn AI."""

from .professions import router as professions_router
from .organizations import router as organizations_router
from .meetings import router as meetings_router
from .conversations import router as conversations_router
from .tasks import router as tasks_router
from .briefings import router as briefings_router
from .interviews import router as interviews_router
from .gdpr import router as gdpr_router
from .metrics import router as metrics_router
from .analytics import router as analytics_router
from .calendar import router as calendar_router
from .sso import router as sso_router
from .api_keys import router as api_keys_router
from .api_keys import webhooks_router
from .white_label import router as white_label_router
from .two_factor import router as two_factor_router
from .webauthn import router as webauthn_router
from .devices import router as devices_router
from .recommendations import router as recommendations_router
from .recommendations import meetings_recommendations_router
from .slack import router as slack_router
from .email_integration import router as email_integration_router
from .zapier import router as zapier_router
from .translation import router as translation_router
from .transcript_editing import router as transcript_editing_router

# Mobile routes
from .mobile import router as mobile_router

# New feature routes
from .personas import router as personas_router
from .collaboration import router as collaboration_router
from .slack_commands import router as slack_commands_router
from .slack_interactive import router as slack_interactive_router
from .compliance import router as compliance_router
from .integrations.pm_integrations import router as pm_integrations_router
from .speakers import router as speakers_router

# Admin routes
from .admin.dashboard import router as admin_dashboard_router
from .admin.teams import router as admin_teams_router
from .admin.tickets import router as admin_tickets_router
from .admin.tickets import customer_router as customer_tickets_router
from .admin.chat import router as admin_chat_router
from .admin.chat import customer_chat_router
from .admin.qa import router as admin_qa_router

__all__ = [
    "professions_router",
    "organizations_router",
    "meetings_router",
    "conversations_router",
    "tasks_router",
    "briefings_router",
    "interviews_router",
    "gdpr_router",
    "metrics_router",
    "analytics_router",
    "calendar_router",
    "sso_router",
    "api_keys_router",
    "webhooks_router",
    "white_label_router",
    "two_factor_router",
    "webauthn_router",
    "devices_router",
    "recommendations_router",
    "meetings_recommendations_router",
    "slack_router",
    "email_integration_router",
    "zapier_router",
    "translation_router",
    "transcript_editing_router",
    # Mobile routes
    "mobile_router",
    # New feature routes
    "personas_router",
    "collaboration_router",
    "slack_commands_router",
    "slack_interactive_router",
    "compliance_router",
    "pm_integrations_router",
    "speakers_router",
    # Admin routes
    "admin_dashboard_router",
    "admin_teams_router",
    "admin_tickets_router",
    "customer_tickets_router",
    "admin_chat_router",
    "customer_chat_router",
    "admin_qa_router",
]
