"""
Subscription management tasks for Celery.

Handles:
- Trial expiration enforcement
- Subscription status synchronization
- Failed payment retry notifications
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User
from config import TRIAL_DAYS

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def enforce_trial_expirations(self) -> Dict[str, Any]:
    """
    Mark expired trial accounts as 'expired'.

    This task should run daily (e.g., at midnight UTC).
    Users whose trial_end_date has passed will have their
    subscription_status set to 'expired'.

    Returns:
        Dictionary with count of processed accounts
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()

        # Find trial users whose trial has expired
        expired_users = db.query(User).filter(
            User.subscription_status == "trial",
            User.trial_end_date < now,
            User.is_staff == False  # Staff never expire
        ).all()

        expired_count = 0
        for user in expired_users:
            user.subscription_status = "expired"
            expired_count += 1
            logger.info(f"Trial expired for user {user.id} ({user.email})")

        if expired_count > 0:
            db.commit()
            logger.info(f"Enforced trial expiration for {expired_count} users")

        return {
            "success": True,
            "expired_count": expired_count,
            "checked_at": now.isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Trial expiration enforcement failed: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_trial_expiration_warnings(self) -> Dict[str, Any]:
    """
    Send warning emails to users whose trial is about to expire.

    Sends warnings at:
    - 3 days before expiration
    - 1 day before expiration
    - On expiration day

    Returns:
        Dictionary with count of warnings sent
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        warning_days = [3, 1, 0]
        warnings_sent = 0

        for days in warning_days:
            # Calculate target date (users expiring in X days)
            target_date = now.date() + timedelta(days=days)

            users = db.query(User).filter(
                User.subscription_status == "trial",
                User.is_staff == False,
                # Trial ends on target date
                User.trial_end_date >= datetime.combine(target_date, datetime.min.time()),
                User.trial_end_date < datetime.combine(target_date + timedelta(days=1), datetime.min.time()),
            ).all()

            for user in users:
                try:
                    # Import here to avoid circular imports
                    from services.email_service import EmailService
                    email_service = EmailService()

                    if days == 0:
                        subject = "Your ReadIn AI trial has ended"
                        message = "Your free trial has ended. Upgrade now to continue enjoying unlimited AI-powered meeting assistance."
                    elif days == 1:
                        subject = "Your ReadIn AI trial ends tomorrow"
                        message = "Don't lose access! Your trial ends tomorrow. Upgrade now to keep your meeting superpowers."
                    else:
                        subject = f"Your ReadIn AI trial ends in {days} days"
                        message = f"Your free trial ends in {days} days. Upgrade to Premium to continue enjoying unlimited features."

                    # Note: You may want to use a proper email template
                    email_service.send_email(
                        to_email=user.email,
                        subject=subject,
                        body=message,
                        template_name="trial_warning"
                    )
                    warnings_sent += 1
                    logger.info(f"Sent {days}-day trial warning to user {user.id}")

                except Exception as e:
                    logger.error(f"Failed to send trial warning to user {user.id}: {e}")

        return {
            "success": True,
            "warnings_sent": warnings_sent,
            "checked_at": now.isoformat()
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Trial warning task failed: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def sync_subscription_status(self) -> Dict[str, Any]:
    """
    Synchronize subscription status with payment providers.

    This task reconciles local subscription status with Stripe/Paystack
    to catch any missed webhooks.

    Should run every few hours.
    """
    import stripe
    from config import STRIPE_SECRET_KEY

    if not STRIPE_SECRET_KEY:
        return {"success": True, "message": "Stripe not configured", "synced": 0}

    stripe.api_key = STRIPE_SECRET_KEY
    db = SessionLocal()

    try:
        synced_count = 0
        errors = []

        # Get users with active Stripe subscriptions
        users_with_stripe = db.query(User).filter(
            User.stripe_customer_id.isnot(None),
            User.subscription_id.isnot(None)
        ).all()

        for user in users_with_stripe:
            try:
                # Fetch subscription from Stripe
                subscription = stripe.Subscription.retrieve(user.subscription_id)

                # Map Stripe status to local status
                status_map = {
                    "active": "active",
                    "past_due": "past_due",
                    "canceled": "cancelled",
                    "unpaid": "past_due",
                    "incomplete": "trial",
                    "incomplete_expired": "expired",
                    "trialing": "trial",
                }

                new_status = status_map.get(subscription.status, user.subscription_status)

                if user.subscription_status != new_status:
                    old_status = user.subscription_status
                    user.subscription_status = new_status
                    synced_count += 1
                    logger.info(
                        f"Synced user {user.id} status: {old_status} -> {new_status}"
                    )

            except stripe.error.InvalidRequestError:
                # Subscription doesn't exist in Stripe
                if user.subscription_status == "active":
                    user.subscription_status = "cancelled"
                    synced_count += 1
                    logger.warning(f"User {user.id} subscription not found in Stripe, marked as cancelled")
            except Exception as e:
                errors.append(f"User {user.id}: {str(e)}")
                logger.error(f"Failed to sync user {user.id}: {e}")

        if synced_count > 0:
            db.commit()

        return {
            "success": True,
            "synced_count": synced_count,
            "total_checked": len(users_with_stripe),
            "errors": errors[:10] if errors else []  # Limit error list
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Subscription sync failed: {e}")
        raise self.retry(exc=e, countdown=300)  # Retry in 5 minutes
    finally:
        db.close()
