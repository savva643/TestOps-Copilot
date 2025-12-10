"""Celery tasks."""

# Only import celery_app here to avoid circular imports
# Tasks will be auto-discovered by celery_app.autodiscover_tasks()
# Explicit import happens in celery_app.py after autodiscover
from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]

