"""Celery application configuration."""

from celery import Celery
from celery.signals import task_prerun, task_postrun
import structlog
from app.core.config import settings

# Import tasks to register them
from app.tasks import test_generation  # noqa: F401

logger = structlog.get_logger()

celery_app = Celery(
    "testops_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Retry on failure
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handler called before task execution."""
    logger.info(
        "Task starting",
        task_id=task_id,
        task_name=task.name if task else None,
    )


@task_postrun.connect
def task_postrun_handler(
    sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds
):
    """Handler called after task execution."""
    logger.info(
        "Task completed",
        task_id=task_id,
        task_name=task.name if task else None,
        state=state,
    )
