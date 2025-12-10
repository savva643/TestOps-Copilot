"""Task status endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Any, List
import structlog

from app.core.security import verify_api_key
from app.tasks.celery_app import celery_app
from app.db import get_db
from app.models import TaskRecord
from sqlalchemy.orm import Session
from sqlalchemy import func

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


class TaskListItem(BaseModel):
    """Single task entry in list."""

    task_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    test_type: Optional[str] = None
    owner: Optional[str] = None
    owner_id: Optional[str] = None
    priority: Optional[str] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Paginated task list."""

    items: List[TaskListItem]
    total: int
    page: int
    page_size: int


def _upsert_task_record(
    db: Session,
    response: dict,
    requester_id: Optional[str] = None,
) -> None:
    """Persist task status snapshot for history."""
    record = db.get(TaskRecord, response["task_id"])
    progress_msg = response.get("progress", {}).get("message") if response.get("progress") else None
    result_summary = None
    result = response.get("result")
    if isinstance(result, dict):
        # Store a compact summary, not full content
        fields = {k: v for k, v in result.items() if k != "test_case"}
        if fields:
            result_summary = str(fields)

    if record:
        record.update_status(
            status=response.get("status", record.status),
            error=response.get("error"),
            progress_message=progress_msg,
            result_summary=result_summary,
        )
        record.updated_at = func.now()
    else:
        record = TaskRecord(
            task_id=response["task_id"],
            status=response.get("status", "unknown"),
            owner_id=requester_id,
            progress_message=progress_msg,
            result_summary=result_summary,
        )
        db.add(record)
    db.commit()


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
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

        # Persist status snapshot for history
        try:
            _upsert_task_record(db, response)
        except Exception as db_err:
            logger.warning("Failed to store task status snapshot", error=str(db_err))

        return TaskStatusResponse(**response)
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e), exc_info=True)
        error_msg = str(e)
        if "generate_test_case" in error_msg.lower():
            error_msg = "Задача не найдена. Убедитесь, что ID задачи правильный и Celery worker запущен."
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(default=None, description="Search by task id"),
    owner_id: Optional[str] = Query(default=None, description="Filter by owner id"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    """Return paginated task list stored in Postgres."""
    query = db.query(TaskRecord)
    if owner_id:
        query = query.filter(TaskRecord.owner_id == owner_id)
    if search:
        ilike = f"%{search}%"
        query = query.filter(TaskRecord.task_id.ilike(ilike))

    total = query.count()
    items = (
        query.order_by(TaskRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )




