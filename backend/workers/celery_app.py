"""
Celery application configuration for background task processing.
"""

import os
from celery import Celery

# Redis URL for broker and backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
celery_app = Celery(
    "readin_workers",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "workers.tasks.summary_generation",
        "workers.tasks.email_tasks",
        "workers.tasks.analytics_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Result backend
    result_expires=3600,  # 1 hour

    # Rate limiting
    task_annotations={
        "workers.tasks.email_tasks.send_email": {"rate_limit": "10/m"},
        "workers.tasks.summary_generation.generate_meeting_summary": {"rate_limit": "5/m"},
    },

    # Scheduled tasks (beat)
    beat_schedule={
        "cleanup-old-cache": {
            "task": "workers.tasks.analytics_tasks.cleanup_old_data",
            "schedule": 86400.0,  # Daily
        },
        "generate-daily-analytics": {
            "task": "workers.tasks.analytics_tasks.generate_daily_analytics",
            "schedule": 86400.0,  # Daily
        },
    },
)


# Optional: Use Redis for task results if available
if CELERY_RESULT_BACKEND.startswith("redis"):
    celery_app.conf.update(
        result_backend=CELERY_RESULT_BACKEND,
        result_extended=True,
    )
