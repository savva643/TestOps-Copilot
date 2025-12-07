"""Celery tasks."""

# Only import celery_app here to avoid circular imports
# Tasks will be auto-discovered by celery_app.autodiscover_tasks()
from app.tasks.celery_app import celery_app

__all__ = ["celery_app"]

