"""
Analytics and maintenance background tasks.
"""

from datetime import datetime, timedelta
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_data() -> dict:
    """
    Clean up old data based on retention policies.

    - Delete inactive trial accounts after 90 days
    - Archive old audit logs after 365 days
    - Clean up orphaned records
    """
    try:
        from database import SessionLocal
        from models import User, AuditLog

        db = SessionLocal()
        deleted_counts = {
            "audit_logs": 0,
            "inactive_trials": 0,
        }

        try:
            # Delete old audit logs (> 365 days)
            year_ago = datetime.utcnow() - timedelta(days=365)
            result = db.query(AuditLog).filter(
                AuditLog.timestamp < year_ago
            ).delete(synchronize_session=False)
            deleted_counts["audit_logs"] = result

            # Mark inactive trial users for cleanup
            # (Just log for now, actual deletion requires more care)
            ninety_days_ago = datetime.utcnow() - timedelta(days=90)
            inactive_trials = db.query(User).filter(
                User.subscription_status == "trialing",
                User.last_login < ninety_days_ago
            ).count()
            deleted_counts["inactive_trials_flagged"] = inactive_trials

            db.commit()

            logger.info(f"Cleanup completed: {deleted_counts}")
            return {"success": True, "deleted": deleted_counts}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task
def generate_daily_analytics() -> dict:
    """
    Generate daily analytics aggregations.
    """
    try:
        from database import SessionLocal
        from models import Meeting, User, Conversation
        from sqlalchemy import func

        db = SessionLocal()

        try:
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            today = datetime.utcnow().date()

            # Count meetings from yesterday
            meetings_count = db.query(Meeting).filter(
                Meeting.started_at >= yesterday,
                Meeting.started_at < today
            ).count()

            # Count active users
            active_users = db.query(func.count(func.distinct(Meeting.user_id))).filter(
                Meeting.started_at >= yesterday,
                Meeting.started_at < today
            ).scalar()

            # Count conversations
            conversations_count = db.query(Conversation).join(Meeting).filter(
                Meeting.started_at >= yesterday,
                Meeting.started_at < today
            ).count()

            # Average meeting duration
            avg_duration = db.query(func.avg(Meeting.duration_seconds)).filter(
                Meeting.started_at >= yesterday,
                Meeting.started_at < today,
                Meeting.duration_seconds.isnot(None)
            ).scalar()

            analytics = {
                "date": str(yesterday),
                "meetings": meetings_count,
                "active_users": active_users or 0,
                "conversations": conversations_count,
                "avg_meeting_duration_seconds": float(avg_duration) if avg_duration else 0,
            }

            logger.info(f"Daily analytics for {yesterday}: {analytics}")
            return {"success": True, "analytics": analytics}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Analytics generation failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task
def update_user_statistics(user_id: int) -> dict:
    """
    Update computed statistics for a user.
    """
    try:
        from database import SessionLocal
        from models import Meeting, Conversation
        from sqlalchemy import func

        db = SessionLocal()

        try:
            # Total meetings
            total_meetings = db.query(Meeting).filter(
                Meeting.user_id == user_id
            ).count()

            # Total conversations
            total_conversations = db.query(Conversation).join(Meeting).filter(
                Meeting.user_id == user_id
            ).count()

            # Total meeting time
            total_duration = db.query(func.sum(Meeting.duration_seconds)).filter(
                Meeting.user_id == user_id,
                Meeting.duration_seconds.isnot(None)
            ).scalar()

            # This week
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_meetings = db.query(Meeting).filter(
                Meeting.user_id == user_id,
                Meeting.started_at >= week_ago
            ).count()

            stats = {
                "user_id": user_id,
                "total_meetings": total_meetings,
                "total_conversations": total_conversations,
                "total_meeting_seconds": total_duration or 0,
                "meetings_this_week": week_meetings,
            }

            # Cache the statistics
            from cache import cache, user_profile_key
            cache.set(f"readin:stats:{user_id}", stats, ttl=900)  # 15 minutes

            return {"success": True, "stats": stats}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"User stats update failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task
def process_subscription_webhook(event_type: str, data: dict) -> dict:
    """
    Process Stripe webhook events asynchronously.
    """
    try:
        from database import SessionLocal
        from models import User

        db = SessionLocal()

        try:
            customer_id = data.get("customer")
            if not customer_id:
                return {"success": False, "error": "No customer ID"}

            user = db.query(User).filter(
                User.stripe_customer_id == customer_id
            ).first()

            if not user:
                logger.warning(f"User not found for Stripe customer: {customer_id}")
                return {"success": False, "error": "User not found"}

            # Process based on event type
            if event_type == "customer.subscription.created":
                user.subscription_status = "active"
                logger.info(f"Subscription created for user {user.id}")

            elif event_type == "customer.subscription.deleted":
                user.subscription_status = "cancelled"
                logger.info(f"Subscription cancelled for user {user.id}")

            elif event_type == "customer.subscription.updated":
                status = data.get("status", "active")
                user.subscription_status = status
                logger.info(f"Subscription updated for user {user.id}: {status}")

            elif event_type == "invoice.payment_failed":
                user.subscription_status = "past_due"
                logger.warning(f"Payment failed for user {user.id}")

            db.commit()

            # Clear user cache
            from cache import cache
            cache.clear_user_cache(user.id)

            return {"success": True, "user_id": user.id, "event": event_type}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {"success": False, "error": str(e)}
