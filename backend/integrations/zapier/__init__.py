"""
Zapier Integration for ReadIn AI.

Provides REST hooks integration for Zapier, enabling users to:
- Trigger workflows when meetings end, action items are created, or summaries are generated
- Create action items and add meeting notes via Zapier actions

Implements Zapier's REST Hook specification:
https://platform.zapier.com/docs/triggers#rest-hook-trigger
"""

from .triggers import (
    ZapierTriggerService,
    TriggerType,
    get_trigger_sample,
    fire_meeting_ended,
    fire_action_item_created,
    fire_summary_generated,
)
from .actions import ZapierActionService, ActionType, get_action_sample, get_action_fields
from .auth import ZapierAuthService, verify_zapier_request, is_zapier_configured

__all__ = [
    "ZapierTriggerService",
    "TriggerType",
    "get_trigger_sample",
    "fire_meeting_ended",
    "fire_action_item_created",
    "fire_summary_generated",
    "ZapierActionService",
    "ActionType",
    "get_action_sample",
    "get_action_fields",
    "ZapierAuthService",
    "verify_zapier_request",
    "is_zapier_configured",
]
