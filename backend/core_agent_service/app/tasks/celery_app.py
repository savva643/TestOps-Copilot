"""Celery application configuration."""

from celery import Celery
from celery.signals import task_prerun, task_postrun
import structlog
from app.core.config import settings

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
    # Redis connection settings to avoid master/replica issues
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_transport_options={
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        },
        'health_check_interval': 30,
        'socket_keepalive': True,
        'socket_keepalive_options': {},
    },
    # Explicitly include task modules
    include=['app.tasks.test_generation'],
)

# Auto-discover tasks to avoid circular imports
celery_app.autodiscover_tasks(['app.tasks'], force=True)

# Explicitly import tasks module after autodiscover to ensure registration
# This ensures the task decorator runs and registers the task
try:
    # Import after celery_app is created to avoid circular imports
    import app.tasks.test_generation  # noqa: F401
    logger.info("Successfully imported test_generation module")
except ImportError as e:
    logger.warning("Failed to import test_generation module", error=str(e))


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
