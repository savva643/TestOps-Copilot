"""Celery tasks."""

from app.tasks.celery_app import celery_app
from app.tasks.test_generation import generate_test_case_task

__all__ = ["celery_app", "generate_test_case_task"]

