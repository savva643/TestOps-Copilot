"""Celery tasks for test generation."""

from typing import Optional, Dict, Any
import structlog
from celery import Task
from app.services.llm_client import LLMClient
from app.services.prompt_engineer import PromptEngineer, PromptValidationError
from app.core.exceptions import LLMError, TaskError

logger = structlog.get_logger()


class ProgressTrackingTask(Task):
    """Custom task class with progress tracking."""

    def update_progress(self, current: int, total: int, message: str = ""):
        """Update task progress."""
        progress = int((current / total) * 100) if total > 0 else 0
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current,
                "total": total,
                "progress": progress,
                "message": message,
            },
        )
        logger.info(
            "Task progress updated",
            task_id=self.request.id,
            progress=progress,
            message=message,
        )


def generate_test_case_task(
    self: ProgressTrackingTask,
    description: str,
    test_type: str = "manual",
    feature: Optional[str] = None,
    story: Optional[str] = None,
    priority: str = "NORMAL",
    owner: Optional[str] = None,
    jira_link: Optional[str] = None,
    llm_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a test case using LLM.

    This is a Celery task that runs asynchronously.
    """
    logger.info(
        "Starting test case generation",
        task_id=self.request.id,
        test_type=test_type,
        priority=priority,
    )

    try:
        # Update progress: 0% - Starting
        self.update_progress(0, 100, "Initializing...")

        # Initialize LLM client with API key if provided
        llm_client = LLMClient(api_key=llm_api_key)

        # Update progress: 20% - Validating and preparing prompts
        self.update_progress(20, 100, "Validating inputs and preparing prompts...")

        # Get prompts (with validation)
        prompt_engineer = PromptEngineer()
        try:
            system_prompt, user_prompt = prompt_engineer.get_test_case_generation_prompt(
                description=description,
                test_type=test_type,
                feature=feature,
                story=story,
            )
        except PromptValidationError as e:
            logger.error("Prompt validation failed", error=str(e))
            raise

        # Update progress: 40% - Calling LLM
        self.update_progress(40, 100, "Generating test case with LLM...")

        # Generate test case
        # Note: This is a sync function, but LLM client is async
        # Create new event loop for async operations
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        generated_text = loop.run_until_complete(
            llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        )

        # Update progress: 80% - Processing result
        self.update_progress(80, 100, "Processing generated test case...")

        # Close client
        loop.run_until_complete(llm_client.close())

        result = {
            "test_case": generated_text,
            "test_type": test_type,
            "feature": feature,
            "story": story,
            "priority": priority,
            "owner": owner,
            "jira_link": jira_link,
        }

        # Update progress: 100% - Complete
        self.update_progress(100, 100, "Test case generated successfully")

        logger.info(
            "Test case generated successfully",
            task_id=self.request.id,
            test_type=test_type,
        )

        return result

    except PromptValidationError as e:
        logger.error("Prompt validation error", task_id=self.request.id, error=str(e))
        raise TaskError(
            "Prompt validation failed",
            details={"task_id": self.request.id, "error": str(e)},
        )
    except LLMError as e:
        logger.error("LLM error", task_id=self.request.id, error=str(e))
        # Retry on LLM errors
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying task after LLM error",
                task_id=self.request.id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=e)
        raise TaskError(
            "Failed to generate test case after retries",
            details={"task_id": self.request.id, "error": str(e)},
        )
    except Exception as e:
        logger.error(
            "Failed to generate test case",
            task_id=self.request.id,
            error=str(e),
            exc_info=True,
        )
        # Retry on certain exceptions
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying task",
                task_id=self.request.id,
                retry_count=self.request.retries + 1,
            )
            raise self.retry(exc=e)
        raise TaskError(
            "Unexpected error during test case generation",
            details={"task_id": self.request.id, "error": str(e)},
        )


# Register task with celery_app to avoid circular import
# Import here after function definition
from app.tasks.celery_app import celery_app

generate_test_case_task = celery_app.task(
    name="generate_test_case",
    bind=True,
    base=ProgressTrackingTask,
    max_retries=3,
    default_retry_delay=60,
)(generate_test_case_task)

