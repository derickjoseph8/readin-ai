"""
Zapier Triggers for ReadIn AI.

Implements REST Hook triggers that fire when events occur:
- meeting_ended: When a meeting session ends
- action_item_created: When a new action item is extracted
- summary_generated: When a meeting summary is created

Zapier REST Hooks specification:
https://platform.zapier.com/docs/triggers#rest-hook-trigger
"""

import logging
import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session

from models import (
    Meeting, ActionItem, MeetingSummary, ZapierSubscription, User
)
from services.webhook_signing import sign_webhook_payload, SIGNATURE_HEADER, TIMESTAMP_HEADER

logger = logging.getLogger("zapier.triggers")


class TriggerType(str, Enum):
    """Available Zapier triggers."""
    MEETING_ENDED = "meeting_ended"
    ACTION_ITEM_CREATED = "action_item_created"
    SUMMARY_GENERATED = "summary_generated"


# Sample data for each trigger type (used by Zapier during setup)
TRIGGER_SAMPLES = {
    TriggerType.MEETING_ENDED: [
        {
            "id": 12345,
            "title": "Weekly Team Standup",
            "meeting_type": "general",
            "meeting_app": "Zoom",
            "started_at": "2024-01-15T10:00:00Z",
            "ended_at": "2024-01-15T10:30:00Z",
            "duration_seconds": 1800,
            "participant_count": 5,
            "status": "ended",
            "action_items_count": 3,
            "user": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
    ],
    TriggerType.ACTION_ITEM_CREATED: [
        {
            "id": 67890,
            "meeting_id": 12345,
            "meeting_title": "Weekly Team Standup",
            "assignee": "Jane Smith",
            "assignee_role": "team",
            "description": "Review the Q4 budget proposal and provide feedback",
            "due_date": "2024-01-22T17:00:00Z",
            "priority": "high",
            "status": "pending",
            "created_at": "2024-01-15T10:30:00Z",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
    ],
    TriggerType.SUMMARY_GENERATED: [
        {
            "id": 11111,
            "meeting_id": 12345,
            "meeting_title": "Weekly Team Standup",
            "summary_text": "The team discussed Q4 progress, upcoming deadlines, and resource allocation. Key decisions were made regarding the product roadmap.",
            "key_points": [
                "Q4 targets are 80% complete",
                "New feature launch scheduled for next month",
                "Additional resources approved for marketing"
            ],
            "decisions_made": [
                "Approved budget increase for Q1",
                "Set new deadline for product launch"
            ],
            "sentiment": "positive",
            "topics_discussed": ["Q4 Progress", "Product Roadmap", "Resource Allocation"],
            "created_at": "2024-01-15T10:35:00Z",
            "user": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
    ]
}


def get_trigger_sample(trigger_type: TriggerType) -> List[Dict[str, Any]]:
    """
    Get sample data for a trigger type.

    Zapier uses this during zap setup to show field mapping options.

    Args:
        trigger_type: The trigger type

    Returns:
        List of sample payloads
    """
    return TRIGGER_SAMPLES.get(trigger_type, [])


class ZapierTriggerService:
    """
    Service for managing Zapier triggers.

    Handles:
    - REST Hook subscription management
    - Webhook delivery to Zapier
    - Retry logic for failed deliveries
    """

    def __init__(self, db: Session):
        """
        Initialize the trigger service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ReadIn-AI-Zapier/1.0",
                }
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # SUBSCRIPTION MANAGEMENT
    # =========================================================================

    def create_subscription(
        self,
        user_id: int,
        trigger_type: TriggerType,
        target_url: str,
        hook_secret: Optional[str] = None
    ) -> ZapierSubscription:
        """
        Create a new webhook subscription.

        Args:
            user_id: User who owns the subscription
            trigger_type: Type of trigger to subscribe to
            target_url: Zapier's webhook URL to send events to
            hook_secret: Optional secret for signing payloads

        Returns:
            Created ZapierSubscription
        """
        subscription = ZapierSubscription(
            user_id=user_id,
            trigger_type=trigger_type.value,
            target_url=target_url,
            hook_secret=hook_secret,
            is_active=True,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        logger.info(
            f"Created Zapier subscription {subscription.id} "
            f"for user {user_id}, trigger {trigger_type.value}"
        )

        return subscription

    def get_subscription(self, subscription_id: int) -> Optional[ZapierSubscription]:
        """
        Get a subscription by ID.

        Args:
            subscription_id: Subscription ID

        Returns:
            ZapierSubscription or None
        """
        return self.db.query(ZapierSubscription).filter(
            ZapierSubscription.id == subscription_id
        ).first()

    def get_user_subscriptions(
        self,
        user_id: int,
        trigger_type: Optional[TriggerType] = None,
        active_only: bool = True
    ) -> List[ZapierSubscription]:
        """
        Get all subscriptions for a user.

        Args:
            user_id: User ID
            trigger_type: Optional filter by trigger type
            active_only: Only return active subscriptions

        Returns:
            List of ZapierSubscription
        """
        query = self.db.query(ZapierSubscription).filter(
            ZapierSubscription.user_id == user_id
        )

        if active_only:
            query = query.filter(ZapierSubscription.is_active == True)

        if trigger_type:
            query = query.filter(ZapierSubscription.trigger_type == trigger_type.value)

        return query.all()

    def delete_subscription(self, subscription_id: int) -> bool:
        """
        Delete a subscription.

        Args:
            subscription_id: Subscription ID

        Returns:
            True if deleted, False if not found
        """
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            return False

        self.db.delete(subscription)
        self.db.commit()

        logger.info(f"Deleted Zapier subscription {subscription_id}")
        return True

    def deactivate_subscription(self, subscription_id: int) -> bool:
        """
        Deactivate a subscription without deleting it.

        Args:
            subscription_id: Subscription ID

        Returns:
            True if deactivated, False if not found
        """
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            return False

        subscription.is_active = False
        self.db.commit()

        logger.info(f"Deactivated Zapier subscription {subscription_id}")
        return True

    # =========================================================================
    # WEBHOOK DELIVERY
    # =========================================================================

    async def fire_trigger(
        self,
        trigger_type: TriggerType,
        user_id: int,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fire a trigger for all active subscriptions.

        Args:
            trigger_type: The type of trigger
            user_id: The user whose subscriptions to fire
            payload: The event payload

        Returns:
            Dictionary with delivery results
        """
        subscriptions = self.get_user_subscriptions(
            user_id=user_id,
            trigger_type=trigger_type,
            active_only=True
        )

        if not subscriptions:
            logger.debug(f"No active subscriptions for user {user_id}, trigger {trigger_type.value}")
            return {"delivered": 0, "failed": 0, "results": []}

        results = []
        delivered = 0
        failed = 0

        for subscription in subscriptions:
            success, error = await self._deliver_webhook(subscription, payload)
            results.append({
                "subscription_id": subscription.id,
                "success": success,
                "error": error
            })

            if success:
                delivered += 1
                # Update last successful delivery
                subscription.last_triggered_at = datetime.utcnow()
                subscription.consecutive_failures = 0
            else:
                failed += 1
                # Track failures for circuit breaker
                subscription.consecutive_failures = (subscription.consecutive_failures or 0) + 1
                subscription.last_error = error

                # Deactivate after too many failures
                if subscription.consecutive_failures >= 10:
                    subscription.is_active = False
                    logger.warning(
                        f"Deactivating subscription {subscription.id} "
                        f"after {subscription.consecutive_failures} consecutive failures"
                    )

        self.db.commit()

        logger.info(
            f"Fired trigger {trigger_type.value} for user {user_id}: "
            f"{delivered} delivered, {failed} failed"
        )

        return {
            "delivered": delivered,
            "failed": failed,
            "results": results
        }

    async def _deliver_webhook(
        self,
        subscription: ZapierSubscription,
        payload: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Deliver a webhook to a single subscription.

        Args:
            subscription: The subscription to deliver to
            payload: The event payload

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Zapier-Event": subscription.trigger_type,
                "X-ReadIn-Subscription-ID": str(subscription.id),
            }

            # Sign the payload if hook_secret is set
            if subscription.hook_secret:
                signature, timestamp = sign_webhook_payload(
                    payload,
                    subscription.hook_secret
                )
                headers[SIGNATURE_HEADER] = signature
                headers[TIMESTAMP_HEADER] = str(timestamp)

            # Send the webhook
            response = await self.client.post(
                subscription.target_url,
                json=payload,
                headers=headers
            )

            # Check response
            if response.status_code in (200, 201, 202, 204):
                return True, None
            elif response.status_code == 410:
                # Gone - Zapier has unsubscribed
                logger.info(f"Subscription {subscription.id} returned 410 Gone, deactivating")
                subscription.is_active = False
                return False, "Subscription removed by Zapier"
            else:
                error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning(f"Webhook delivery failed for subscription {subscription.id}: {error}")
                return False, error

        except httpx.TimeoutException:
            return False, "Request timeout"
        except httpx.RequestError as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error delivering webhook: {e}")
            return False, f"Unexpected error: {str(e)}"

    # =========================================================================
    # EVENT PAYLOAD BUILDERS
    # =========================================================================

    def build_meeting_ended_payload(
        self,
        meeting: Meeting,
        user: User
    ) -> Dict[str, Any]:
        """
        Build payload for meeting_ended trigger.

        Args:
            meeting: The Meeting that ended
            user: The meeting owner

        Returns:
            Trigger payload
        """
        action_items_count = len(meeting.action_items) if meeting.action_items else 0

        return {
            "id": meeting.id,
            "title": meeting.title,
            "meeting_type": meeting.meeting_type,
            "meeting_app": meeting.meeting_app,
            "started_at": meeting.started_at.isoformat() if meeting.started_at else None,
            "ended_at": meeting.ended_at.isoformat() if meeting.ended_at else None,
            "duration_seconds": meeting.duration_seconds,
            "participant_count": meeting.participant_count,
            "status": meeting.status,
            "action_items_count": action_items_count,
            "notes": meeting.notes,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        }

    def build_action_item_created_payload(
        self,
        action_item: ActionItem,
        meeting: Meeting,
        user: User
    ) -> Dict[str, Any]:
        """
        Build payload for action_item_created trigger.

        Args:
            action_item: The created ActionItem
            meeting: The associated Meeting
            user: The action item owner

        Returns:
            Trigger payload
        """
        return {
            "id": action_item.id,
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "assignee": action_item.assignee,
            "assignee_role": action_item.assignee_role,
            "description": action_item.description,
            "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
            "priority": action_item.priority,
            "status": action_item.status,
            "created_at": action_item.created_at.isoformat() if action_item.created_at else None,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        }

    def build_summary_generated_payload(
        self,
        summary: MeetingSummary,
        meeting: Meeting,
        user: User
    ) -> Dict[str, Any]:
        """
        Build payload for summary_generated trigger.

        Args:
            summary: The generated MeetingSummary
            meeting: The associated Meeting
            user: The meeting owner

        Returns:
            Trigger payload
        """
        return {
            "id": summary.id,
            "meeting_id": meeting.id,
            "meeting_title": meeting.title,
            "summary_text": summary.summary_text,
            "key_points": summary.key_points or [],
            "decisions_made": summary.decisions_made or [],
            "sentiment": summary.sentiment,
            "topics_discussed": summary.topics_discussed or [],
            "created_at": summary.created_at.isoformat() if summary.created_at else None,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
            }
        }


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

async def fire_meeting_ended(
    db: Session,
    meeting: Meeting,
    user: User
) -> Dict[str, Any]:
    """
    Fire the meeting_ended trigger.

    Args:
        db: Database session
        meeting: The Meeting that ended
        user: The meeting owner

    Returns:
        Delivery results
    """
    service = ZapierTriggerService(db)
    try:
        payload = service.build_meeting_ended_payload(meeting, user)
        return await service.fire_trigger(
            TriggerType.MEETING_ENDED,
            user.id,
            payload
        )
    finally:
        await service.close()


async def fire_action_item_created(
    db: Session,
    action_item: ActionItem,
    meeting: Meeting,
    user: User
) -> Dict[str, Any]:
    """
    Fire the action_item_created trigger.

    Args:
        db: Database session
        action_item: The created ActionItem
        meeting: The associated Meeting
        user: The action item owner

    Returns:
        Delivery results
    """
    service = ZapierTriggerService(db)
    try:
        payload = service.build_action_item_created_payload(action_item, meeting, user)
        return await service.fire_trigger(
            TriggerType.ACTION_ITEM_CREATED,
            user.id,
            payload
        )
    finally:
        await service.close()


async def fire_summary_generated(
    db: Session,
    summary: MeetingSummary,
    meeting: Meeting,
    user: User
) -> Dict[str, Any]:
    """
    Fire the summary_generated trigger.

    Args:
        db: Database session
        summary: The generated MeetingSummary
        meeting: The associated Meeting
        user: The meeting owner

    Returns:
        Delivery results
    """
    service = ZapierTriggerService(db)
    try:
        payload = service.build_summary_generated_payload(summary, meeting, user)
        return await service.fire_trigger(
            TriggerType.SUMMARY_GENERATED,
            user.id,
            payload
        )
    finally:
        await service.close()
