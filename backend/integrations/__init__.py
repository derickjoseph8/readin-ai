"""
Third-party integrations for ReadIn AI.

This package contains integrations for:
- Project Management: Notion, Asana, Linear, Jira
- CRM: Salesforce, HubSpot (existing in services/)
- Communication: Slack (slack-bolt app), Teams (existing in services/)
- Calendar: Google, Microsoft, Apple, Calendly (existing in services/)
- Automation: Zapier (REST Hooks)
"""

# Slack integration (optional - requires slack-bolt)
try:
    from .slack_app import (
        get_slack_app,
        is_slack_app_configured,
        create_slack_handler,
        SlackDailyDigest,
        send_meeting_summary_notification,
        send_action_item_reminder,
    )
    _SLACK_AVAILABLE = True
except ImportError:
    _SLACK_AVAILABLE = False

    # Provide stub functions when slack-bolt is not installed
    def get_slack_app():
        raise ImportError("slack-bolt is not installed")

    def is_slack_app_configured():
        return False

    def create_slack_handler(*args, **kwargs):
        raise ImportError("slack-bolt is not installed")

    class SlackDailyDigest:
        pass

    async def send_meeting_summary_notification(*args, **kwargs):
        pass

    async def send_action_item_reminder(*args, **kwargs):
        pass


# Zapier integration
from .zapier import (
    ZapierTriggerService,
    TriggerType,
    ZapierActionService,
    ActionType,
    ZapierAuthService,
    verify_zapier_request,
    fire_meeting_ended,
    fire_action_item_created,
    fire_summary_generated,
)
from .zapier.triggers import get_trigger_sample
from .zapier.actions import get_action_sample, get_action_fields
from .zapier.auth import is_zapier_configured


__all__ = [
    # Slack
    "get_slack_app",
    "is_slack_app_configured",
    "create_slack_handler",
    "SlackDailyDigest",
    "send_meeting_summary_notification",
    "send_action_item_reminder",
    # Zapier
    "ZapierTriggerService",
    "TriggerType",
    "ZapierActionService",
    "ActionType",
    "ZapierAuthService",
    "verify_zapier_request",
    "fire_meeting_ended",
    "fire_action_item_created",
    "fire_summary_generated",
    "get_trigger_sample",
    "get_action_sample",
    "get_action_fields",
    "is_zapier_configured",
]
