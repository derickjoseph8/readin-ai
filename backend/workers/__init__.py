"""
Background workers for ReadIn AI.

Uses Celery for async task processing:
- Meeting summary generation
- Email notifications
- Analytics processing
"""

from .celery_app import celery_app

__all__ = ["celery_app"]
