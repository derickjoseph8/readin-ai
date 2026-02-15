"""Background Scheduler Service for automated tasks."""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import (
    Commitment,
    Meeting,
    MeetingSummary,
    User,
    UserLearningProfile,
)
from database import SessionLocal


class SchedulerService:
    """Background job scheduler for automated tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    def start(self):
        """Start the scheduler with all jobs."""
        if self._is_running:
            return

        # Check commitment reminders every 15 minutes
        self.scheduler.add_job(
            self._check_commitment_reminders,
            IntervalTrigger(minutes=15),
            id="commitment_reminders",
            replace_existing=True,
        )

        # Process pending meeting summaries every 5 minutes
        self.scheduler.add_job(
            self._process_pending_summaries,
            IntervalTrigger(minutes=5),
            id="pending_summaries",
            replace_existing=True,
        )

        # Update ML patterns daily at 2 AM
        self.scheduler.add_job(
            self._update_ml_patterns,
            CronTrigger(hour=2, minute=0),
            id="ml_patterns_update",
            replace_existing=True,
        )

        # Send weekly digests on Monday at 8 AM
        self.scheduler.add_job(
            self._send_weekly_digests,
            CronTrigger(day_of_week="mon", hour=8, minute=0),
            id="weekly_digests",
            replace_existing=True,
        )

        # Clean up old data monthly
        self.scheduler.add_job(
            self._cleanup_old_data,
            CronTrigger(day=1, hour=3, minute=0),
            id="monthly_cleanup",
            replace_existing=True,
        )

        # Run GDPR data retention tasks daily at 4 AM
        self.scheduler.add_job(
            self._run_data_retention_tasks,
            CronTrigger(hour=4, minute=0),
            id="data_retention",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True
        print("Scheduler started with all jobs")

    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            print("Scheduler stopped")

    async def _check_commitment_reminders(self):
        """Check for commitments that need reminders."""
        db = SessionLocal()
        try:
            from .email_service import EmailService

            email_service = EmailService(db)

            if not email_service.is_configured():
                print("Email service not configured, skipping reminders")
                return

            reminder_hours = int(
                os.getenv("COMMITMENT_REMINDER_HOURS_BEFORE", "24")
            )
            reminder_threshold = datetime.utcnow() + timedelta(hours=reminder_hours)

            # Find commitments due soon that haven't been reminded
            commitments = (
                db.query(Commitment)
                .filter(
                    and_(
                        Commitment.status == "pending",
                        Commitment.due_date <= reminder_threshold,
                        Commitment.due_date > datetime.utcnow(),
                        Commitment.reminder_sent == False,
                    )
                )
                .all()
            )

            for commitment in commitments:
                result = await email_service.send_commitment_reminder(
                    user_id=commitment.user_id,
                    commitment_description=commitment.description,
                    due_date=commitment.due_date,
                )

                if result.get("success"):
                    commitment.reminder_sent = True
                    commitment.last_reminder_at = datetime.utcnow()
                    print(f"Sent reminder for commitment {commitment.id}")
                else:
                    print(f"Failed to send reminder: {result.get('error')}")

            db.commit()

        except Exception as e:
            print(f"Error checking commitment reminders: {e}")
            db.rollback()
        finally:
            db.close()

    async def _process_pending_summaries(self):
        """Process meetings that need summaries."""
        db = SessionLocal()
        try:
            from .summary_generator import SummaryGenerator
            from .email_service import EmailService

            summary_gen = SummaryGenerator(db)
            email_service = EmailService(db)

            # Find ended meetings without summaries
            meetings = (
                db.query(Meeting)
                .outerjoin(MeetingSummary)
                .filter(
                    and_(
                        Meeting.ended_at.isnot(None),
                        MeetingSummary.id.is_(None),
                    )
                )
                .limit(10)
                .all()
            )

            for meeting in meetings:
                try:
                    # Generate summary
                    summary = await summary_gen.generate_summary(meeting.id)

                    # Send email if configured
                    if email_service.is_configured():
                        email_content = await summary_gen.generate_email_content(
                            meeting.id
                        )
                        result = await email_service.send_meeting_summary(
                            user_id=meeting.user_id,
                            meeting_id=meeting.id,
                            summary_content=email_content,
                        )

                        if result.get("success"):
                            summary.email_sent = True
                            summary.email_sent_at = datetime.utcnow()
                            db.commit()

                    print(f"Processed summary for meeting {meeting.id}")

                except Exception as e:
                    print(f"Error processing meeting {meeting.id}: {e}")

        except Exception as e:
            print(f"Error processing pending summaries: {e}")
        finally:
            db.close()

    async def _update_ml_patterns(self):
        """Update ML patterns for all active users."""
        db = SessionLocal()
        try:
            from .pattern_analyzer import PatternAnalyzer
            from .topic_extractor import TopicExtractor

            pattern_analyzer = PatternAnalyzer(db)
            topic_extractor = TopicExtractor(db)

            # Get users with recent activity
            recent_threshold = datetime.utcnow() - timedelta(days=7)
            active_users = (
                db.query(User)
                .join(Meeting)
                .filter(Meeting.started_at >= recent_threshold)
                .distinct()
                .all()
            )

            for user in active_users:
                try:
                    # Update pattern analysis
                    await pattern_analyzer.update_learning_profile(user.id)

                    # Update topic profile
                    await topic_extractor.update_learning_profile_topics(user.id)

                    print(f"Updated ML patterns for user {user.id}")

                except Exception as e:
                    print(f"Error updating patterns for user {user.id}: {e}")

        except Exception as e:
            print(f"Error in ML pattern update: {e}")
        finally:
            db.close()

    async def _send_weekly_digests(self):
        """Send weekly digest emails to all users."""
        db = SessionLocal()
        try:
            from .email_service import EmailService

            email_service = EmailService(db)

            if not email_service.is_configured():
                print("Email service not configured, skipping digests")
                return

            # Get users with email enabled
            users = (
                db.query(User)
                .filter(User.email_notifications_enabled == True)
                .all()
            )

            week_ago = datetime.utcnow() - timedelta(days=7)

            for user in users:
                try:
                    # Get week's data
                    meetings = (
                        db.query(Meeting)
                        .filter(
                            Meeting.user_id == user.id,
                            Meeting.started_at >= week_ago,
                        )
                        .all()
                    )

                    from models import ActionItem, Commitment

                    actions_completed = (
                        db.query(ActionItem)
                        .filter(
                            ActionItem.user_id == user.id,
                            ActionItem.completed_at >= week_ago,
                        )
                        .count()
                    )

                    commitments_fulfilled = (
                        db.query(Commitment)
                        .filter(
                            Commitment.user_id == user.id,
                            Commitment.status == "completed",
                            Commitment.completed_at >= week_ago,
                        )
                        .count()
                    )

                    pending_actions = (
                        db.query(ActionItem)
                        .filter(
                            ActionItem.user_id == user.id,
                            ActionItem.status == "pending",
                        )
                        .limit(5)
                        .all()
                    )

                    digest_data = {
                        "meeting_count": len(meetings),
                        "meetings": [
                            {
                                "title": m.title or "Untitled",
                                "date": m.started_at.strftime("%Y-%m-%d"),
                            }
                            for m in meetings[:5]
                        ],
                        "actions_completed": actions_completed,
                        "commitments_fulfilled": commitments_fulfilled,
                        "pending_actions": [
                            {"description": a.description} for a in pending_actions
                        ],
                    }

                    await email_service.send_weekly_digest(user.id, digest_data)
                    print(f"Sent weekly digest to user {user.id}")

                except Exception as e:
                    print(f"Error sending digest to user {user.id}: {e}")

        except Exception as e:
            print(f"Error in weekly digest: {e}")
        finally:
            db.close()

    async def _cleanup_old_data(self):
        """Clean up old data according to retention policy."""
        db = SessionLocal()
        try:
            retention_days = int(os.getenv("DATA_RETENTION_DAYS", "90"))
            cutoff = datetime.utcnow() - timedelta(days=retention_days)

            # Delete old conversations (keeping meetings for reference)
            from models import Conversation

            deleted = (
                db.query(Conversation)
                .filter(Conversation.created_at < cutoff)
                .delete()
            )

            print(f"Cleaned up {deleted} old conversations")

            db.commit()

        except Exception as e:
            print(f"Error in cleanup: {e}")
            db.rollback()
        finally:
            db.close()

    async def _run_data_retention_tasks(self):
        """Run GDPR data retention tasks."""
        db = SessionLocal()
        try:
            from .data_retention import DataRetentionService

            retention_service = DataRetentionService(db)

            # Process scheduled account deletions
            print("Processing scheduled deletions...")
            deletion_result = retention_service.process_scheduled_deletions()
            print(f"Deletion processing result: {deletion_result}")

            # Flag inactive trial accounts
            print("Checking for inactive trial accounts...")
            trial_result = retention_service.cleanup_inactive_trials()
            print(f"Trial cleanup result: {trial_result}")

            # Clean up old audit logs
            print("Cleaning up old audit logs...")
            deleted_logs = retention_service.cleanup_old_audit_logs()
            print(f"Deleted {deleted_logs} old audit log entries")

            # Archive old meetings
            print("Archiving old meetings...")
            archived_meetings = retention_service.archive_old_meetings()
            print(f"Found {archived_meetings} meetings eligible for archival")

            # Generate retention report for compliance
            report = retention_service.get_retention_report()
            print(f"Data retention report: {report}")

            print("Data retention tasks completed successfully")

        except Exception as e:
            print(f"Error in data retention tasks: {e}")
            db.rollback()
        finally:
            db.close()

    def add_job(
        self,
        func: Callable,
        trigger: str,
        job_id: str,
        **trigger_args,
    ):
        """Add a custom job to the scheduler."""
        if trigger == "interval":
            trigger_obj = IntervalTrigger(**trigger_args)
        elif trigger == "cron":
            trigger_obj = CronTrigger(**trigger_args)
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")

        self.scheduler.add_job(
            func,
            trigger_obj,
            id=job_id,
            replace_existing=True,
        )

    def remove_job(self, job_id: str):
        """Remove a job from the scheduler."""
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    def get_jobs(self) -> List[dict]:
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self.scheduler.get_jobs()
        ]


# Singleton instance
_scheduler: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get or create scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
