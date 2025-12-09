"""Test generation endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
import structlog

from app.core.security import verify_api_key
from app.services.llm_client import LLMClient
from app.tasks.test_generation import generate_test_case_task

logger = structlog.get_logger()

router = APIRouter()


class TestCaseGenerationRequest(BaseModel):
    """Request model for test case generation."""

    description: str
    test_type: str = "manual"  # manual, api, ui
    feature: Optional[str] = None
    story: Optional[str] = None
    priority: str = "NORMAL"  # CRITICAL, NORMAL, LOW
    owner: Optional[str] = None
    jira_link: Optional[str] = None


class TestCaseGenerationResponse(BaseModel):
    """Response model for test case generation."""

    task_id: str
    status: str
    message: str


@router.post("/test-case", response_model=TestCaseGenerationResponse)
async def generate_test_case(
    request: TestCaseGenerationRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Generate a test case based on description.
    
    This endpoint accepts a description and generates a structured test case
    using the Cloud.ru Evolution Foundation Model.
    """
    # Get LLM API key from header if provided
    llm_api_key = http_request.headers.get("X-LLM-API-Key")
    
    try:
        # Create async task
        task = generate_test_case_task.delay(
            description=request.description,
            test_type=request.test_type,
            feature=request.feature,
            story=request.story,
            priority=request.priority,
            owner=request.owner,
            jira_link=request.jira_link,
            llm_api_key=llm_api_key,
        )

        logger.info(
            "Test case generation task created",
            task_id=task.id,
            test_type=request.test_type,
        )

        return TestCaseGenerationResponse(
            task_id=task.id,
            status="pending",
            message="Задача генерации тест-кейса создана",
        )
    except Exception as e:
        logger.error("Failed to create test case generation task", error=str(e), exc_info=True)
        error_msg = str(e)
        if "generate_test_case" in error_msg.lower():
            error_msg = "Ошибка создания задачи генерации. Убедитесь, что Celery worker запущен."
        raise HTTPException(status_code=500, detail=error_msg)




