"""Task status endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
import structlog

from app.core.security import verify_api_key
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()

router = APIRouter()


class ProgressInfo(BaseModel):
    """Progress information model."""

    current: int
    total: int
    percentage: int
    message: str


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[ProgressInfo] = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Get the status of a Celery task."""
    try:
        task = celery_app.AsyncResult(task_id)

        if task.state == "PENDING":
            response = {
                "task_id": task_id,
                "status": "pending",
                "result": None,
                "error": None,
                "progress": None,
            }
        elif task.state == "PROGRESS":
            # Task is in progress, include progress info
            meta = task.info if isinstance(task.info, dict) else {}
            response = {
                "task_id": task_id,
                "status": "in_progress",
                "result": None,
                "error": None,
                "progress": {
                    "current": meta.get("current", 0),
                    "total": meta.get("total", 100),
                    "percentage": meta.get("progress", 0),
                    "message": meta.get("message", "Processing..."),
                },
            }
        elif task.state == "SUCCESS":
            response = {
                "task_id": task_id,
                "status": "completed",
                "result": task.result,
                "error": None,
                "progress": {
                    "current": 100,
                    "total": 100,
                    "percentage": 100,
                    "message": "Completed",
                },
            }
        elif task.state == "FAILURE":
            response = {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": str(task.info),
                "progress": None,
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state.lower(),
                "result": task.result if task.result else None,
                "error": None,
                "progress": None,
            }

        return TaskStatusResponse(**response)
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))




