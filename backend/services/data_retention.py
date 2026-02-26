"""
Data retention service for GDPR compliance.

Handles:
- Scheduled account deletions
- Data archival
- Retention policy enforcement
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataRetentionService:
    """
    Manages data retention and scheduled deletions.
    """

    # Retention periods (in days)
    TRIAL_INACTIVE_DAYS = 90      # Delete inactive trial accounts after 90 days
    CANCELLED_RETENTION_DAYS = 365  # Keep cancelled account data for 1 year
    AUDIT_LOG_RETENTION_DAYS = 365  # Keep audit logs for 1 year
    MEETING_ARCHIVE_DAYS = 730    # Archive meetings older than 2 years

    def __init__(self, db_session):
        self.db = db_session

    def process_scheduled_deletions(self) -> dict:
        """
        Process accounts scheduled for deletion.
        Run this daily via cron/scheduler.
        """
        from models import User

        now = datetime.utcnow()
        deleted_count = 0

        # Find users scheduled for deletion
        users_to_delete = self.db.query(User).filter(
            User.deletion_requested == True,
            User.deletion_scheduled <= now
        ).all()

        for user in users_to_delete:
            try:
                self._delete_user_data(user.id)
                deleted_count += 1
                logger.info(f"Deleted scheduled account: {user.id}")
            except Exception as e:
                logger.error(f"Failed to delete user {user.id}: {e}")

        return {
            "processed": len(users_to_delete),
            "deleted": deleted_count
        }

    def cleanup_inactive_trials(self) -> dict:
        """
        Mark inactive trial accounts for deletion.
        """
        from models import User

        cutoff = datetime.utcnow() - timedelta(days=self.TRIAL_INACTIVE_DAYS)
        flagged_count = 0

        # Find inactive trial users
        inactive_trials = self.db.query(User).filter(
            User.subscription_status == "trialing",
            User.last_login < cutoff,
            User.deletion_requested == False
        ).all()

        for user in inactive_trials:
            # Schedule for deletion (give 30 days notice)
            user.deletion_requested = True
            deletion_date = datetime.utcnow() + timedelta(days=30)
            user.deletion_scheduled = deletion_date
            flagged_count += 1

            # Send notification email
            try:
                import asyncio
                from services.email_service import EmailService
                email_service = EmailService(self.db)
                asyncio.create_task(
                    email_service.send_account_deletion_warning(
                        user_id=user.id,
                        deletion_date=deletion_date,
                        days_remaining=30,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to send deletion warning email to user {user.id}: {e}")

            logger.info(f"Flagged inactive trial for deletion: {user.id}")

        self.db.commit()

        return {
            "inactive_found": len(inactive_trials),
            "flagged_for_deletion": flagged_count
        }

    def cleanup_old_audit_logs(self) -> int:
        """
        Delete audit logs older than retention period.
        """
        from models import AuditLog

        cutoff = datetime.utcnow() - timedelta(days=self.AUDIT_LOG_RETENTION_DAYS)

        deleted = self.db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff
        ).delete(synchronize_session=False)

        self.db.commit()

        logger.info(f"Deleted {deleted} old audit logs")
        return deleted

    def archive_old_meetings(self) -> int:
        """
        Archive meetings older than retention period.
        In production, this would move data to cold storage.
        """
        from models import Meeting

        cutoff = datetime.utcnow() - timedelta(days=self.MEETING_ARCHIVE_DAYS)

        # For now, just count - in production would archive to S3/cold storage
        old_meetings = self.db.query(Meeting).filter(
            Meeting.started_at < cutoff
        ).count()

        logger.info(f"Found {old_meetings} meetings eligible for archival")
        return old_meetings

    def _delete_user_data(self, user_id: int):
        """
        Delete all data for a user.
        """
        from models import (
            User, Meeting, Conversation, MeetingSummary,
            ActionItem, Commitment, UserLearningProfile,
            ParticipantMemory, PreMeetingBriefing, AuditLog, Topic
        )

        # Delete in order (respecting foreign keys)
        self.db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        self.db.query(UserLearningProfile).filter(UserLearningProfile.user_id == user_id).delete()
        self.db.query(ParticipantMemory).filter(ParticipantMemory.user_id == user_id).delete()
        self.db.query(PreMeetingBriefing).filter(PreMeetingBriefing.user_id == user_id).delete()
        self.db.query(ActionItem).filter(ActionItem.user_id == user_id).delete()
        self.db.query(Topic).filter(Topic.user_id == user_id).delete()

        # Delete meetings and related data
        meetings = self.db.query(Meeting).filter(Meeting.user_id == user_id).all()
        for meeting in meetings:
            self.db.query(Conversation).filter(Conversation.meeting_id == meeting.id).delete()
            self.db.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting.id).delete()
            self.db.query(Commitment).filter(Commitment.meeting_id == meeting.id).delete()
            self.db.delete(meeting)

        # Delete user
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            self.db.delete(user)

        self.db.commit()

        # Clear cache
        from cache import cache
        cache.clear_user_cache(user_id)

    def anonymize_user_data(self, user_id: int):
        """
        Anonymize user data instead of deleting.
        Used when we need to keep meeting data for analytics.
        """
        from models import User, Meeting, Conversation, ParticipantMemory

        # Anonymize user
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.email = f"deleted_{user.id}@anonymized.local"
            user.full_name = "Deleted User"
            user.hashed_password = None
            user.stripe_customer_id = None

        # Anonymize participant memories
        self.db.query(ParticipantMemory).filter(
            ParticipantMemory.user_id == user_id
        ).update({
            "participant_name": "Anonymous",
            "notes": None
        })

        # Keep meeting metadata but remove personal notes
        self.db.query(Meeting).filter(
            Meeting.user_id == user_id
        ).update({
            "notes": None
        })

        self.db.commit()
        logger.info(f"Anonymized data for user {user_id}")

    def get_retention_report(self) -> dict:
        """
        Generate a report on data retention status.
        """
        from models import User, Meeting, AuditLog

        now = datetime.utcnow()

        # Scheduled deletions
        pending_deletions = self.db.query(User).filter(
            User.deletion_requested == True
        ).count()

        # Inactive trials
        trial_cutoff = now - timedelta(days=self.TRIAL_INACTIVE_DAYS)
        inactive_trials = self.db.query(User).filter(
            User.subscription_status == "trialing",
            User.last_login < trial_cutoff
        ).count()

        # Old audit logs
        audit_cutoff = now - timedelta(days=self.AUDIT_LOG_RETENTION_DAYS)
        old_audit_logs = self.db.query(AuditLog).filter(
            AuditLog.timestamp < audit_cutoff
        ).count()

        # Old meetings
        meeting_cutoff = now - timedelta(days=self.MEETING_ARCHIVE_DAYS)
        archivable_meetings = self.db.query(Meeting).filter(
            Meeting.started_at < meeting_cutoff
        ).count()

        return {
            "report_date": now.isoformat(),
            "pending_deletions": pending_deletions,
            "inactive_trial_accounts": inactive_trials,
            "old_audit_logs": old_audit_logs,
            "archivable_meetings": archivable_meetings,
            "retention_policies": {
                "trial_inactive_days": self.TRIAL_INACTIVE_DAYS,
                "cancelled_retention_days": self.CANCELLED_RETENTION_DAYS,
                "audit_log_retention_days": self.AUDIT_LOG_RETENTION_DAYS,
                "meeting_archive_days": self.MEETING_ARCHIVE_DAYS,
            }
        }


def run_daily_retention_tasks():
    """
    Run all daily retention tasks.
    Should be called by scheduler/cron.
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        service = DataRetentionService(db)

        # Process scheduled deletions
        deletion_result = service.process_scheduled_deletions()
        logger.info(f"Deletion processing: {deletion_result}")

        # Cleanup inactive trials
        trial_result = service.cleanup_inactive_trials()
        logger.info(f"Trial cleanup: {trial_result}")

        # Cleanup old audit logs
        audit_result = service.cleanup_old_audit_logs()
        logger.info(f"Audit log cleanup: {audit_result}")

        # Generate report
        report = service.get_retention_report()
        logger.info(f"Retention report: {report}")

        return {
            "success": True,
            "deletions": deletion_result,
            "trials": trial_result,
            "audit_logs": audit_result,
            "report": report
        }

    except Exception as e:
        logger.error(f"Retention tasks failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        db.close()
