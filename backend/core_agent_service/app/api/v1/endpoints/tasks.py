"""Task status endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
import structlog

from app.core.security import verify_api_key
from app.tasks.celery_app import celery_app
from app.db import get_db
from app.models import TaskRecord, TaskArtifact
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
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


def _safe_extract_error(task_info: Any) -> str:
    """Safely extract error message from Celery task info."""
    if task_info is None:
        return "Unknown error"
    
    # If it's already a string, return it
    if isinstance(task_info, str):
        return task_info
    
    # If it's an exception object, extract the message
    if isinstance(task_info, Exception):
        error_msg = str(task_info)
        # If it has a message attribute, use it
        if hasattr(task_info, 'message'):
            error_msg = task_info.message
        # If it has details, include them
        if hasattr(task_info, 'details') and task_info.details:
            details_str = str(task_info.details)
            if details_str:
                error_msg = f"{error_msg}: {details_str}"
        return error_msg
    
    # If it's a dict, try to extract error information
    if isinstance(task_info, dict):
        # Celery sometimes stores exception info in a dict
        if 'exc_type' in task_info and 'exc_message' in task_info:
            exc_type = task_info.get('exc_type', 'UnknownError')
            exc_message = task_info.get('exc_message', '')
            return f"{exc_type}: {exc_message}"
        # Or it might have an 'error' key
        if 'error' in task_info:
            return _safe_extract_error(task_info['error'])
        # Or just convert the whole dict to string
        return str(task_info)
    
    # For any other type, convert to string
    try:
        return str(task_info)
    except Exception:
        return "Unable to extract error message"


def _safe_serialize_result(result: Any) -> Optional[Any]:
    """Safely serialize task result, converting any exception objects to strings."""
    if result is None:
        return None
    
    # If result contains exception objects, convert them
    if isinstance(result, Exception):
        return _safe_extract_error(result)
    
    if isinstance(result, dict):
        # Recursively check dict values
        return {k: _safe_serialize_result(v) for k, v in result.items()}
    
    if isinstance(result, (list, tuple)):
        # Recursively check list items
        return [_safe_serialize_result(item) for item in result]
    
    return result


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
        # Store a compact summary, без тяжёлого содержимого тестов
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

    # Если в результате есть тесты, сохраняем их как артефакты в БД,
    # чтобы они были доступны с любого устройства, независимо от Celery.
    if isinstance(result, dict) and "test_case" in result:
        test_case = result["test_case"]
        artifacts: list[TaskArtifact] = []

        # Новая структура: {"files": [{filename, code, description}]}
        if isinstance(test_case, dict) and isinstance(test_case.get("files"), list):
            for file in test_case["files"]:
                filename = str(file.get("filename") or "test.py")
                code = str(file.get("code") or "")
                description = file.get("description")
                if not code:
                    continue
                artifacts.append(
                    TaskArtifact(
                        task_id=response["task_id"],
                        filename=filename,
                        description=description,
                        content=code,
                    )
                )
        # Старая структура: test_case как строка
        elif isinstance(test_case, str):
            is_manual = str(result.get("test_type", "")).lower() == "manual"
            filename = "manual_test_case.md" if is_manual else "test.py"
            if test_case.strip():
                artifacts.append(
                    TaskArtifact(
                        task_id=response["task_id"],
                        filename=filename,
                        description=None,
                        content=test_case,
                    )
                )

        if artifacts:
            # Удаляем старые артефакты для этой задачи и сохраняем новые снимком
            db.query(TaskArtifact).filter(TaskArtifact.task_id == response["task_id"]).delete()
            for artifact in artifacts:
                db.add(artifact)

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

        # Проверяем, существует ли задача в БД
        db_record = db.get(TaskRecord, task_id)
        
        if task.state == "PENDING":
            # Если задача в PENDING и нет записи в БД, значит задача не существует
            if not db_record:
                raise HTTPException(status_code=404, detail="Задача с таким ID не найдена в базе данных")
            
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
            # Safely serialize result to ensure no exception objects
            safe_result = _safe_serialize_result(task.result)
            response = {
                "task_id": task_id,
                "status": "completed",
                "result": safe_result,
                "error": None,
                "progress": {
                    "current": 100,
                    "total": 100,
                    "percentage": 100,
                    "message": "Completed",
                },
            }
        elif task.state == "FAILURE":
            # Safely extract error message from task.info
            error_message = _safe_extract_error(task.info)
            response = {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": error_message,
                "progress": None,
            }
        else:
            # Safely serialize result for other states
            safe_result = _safe_serialize_result(task.result) if task.result else None
            response = {
                "task_id": task_id,
                "status": task.state.lower(),
                "result": safe_result,
                "error": None,
                "progress": None,
            }

        # Persist status snapshot and artifacts for history
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


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
    search: Optional[str] = Query(default=None, description="Search by task id"),
    owner_id: Optional[str] = Query(default=None, description="Filter by owner id"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    """Return paginated task list stored in Postgres."""
    # Build base query
    query = db.query(TaskRecord)
    if owner_id:
        query = query.filter(TaskRecord.owner_id == owner_id)
    if search:
        ilike = f"%{search}%"
        query = query.filter(TaskRecord.task_id.ilike(ilike))

    # For count, use func.count to avoid selecting all columns
    total = db.query(func.count(TaskRecord.task_id))
    if owner_id:
        total = total.filter(TaskRecord.owner_id == owner_id)
    if search:
        ilike = f"%{search}%"
        total = total.filter(TaskRecord.task_id.ilike(ilike))
    total = total.scalar() or 0
    
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


class TaskFile(BaseModel):
    """Single test file attached to a task."""

    filename: str
    description: Optional[str] = None
    content: str


class TaskArtifactsResponse(BaseModel):
    """Full set of test files for a task, loaded from DB."""

    task_id: str
    test_type: Optional[str] = None
    priority: Optional[str] = None
    feature: Optional[str] = None
    files: List[TaskFile]


@router.get("/{task_id}/artifacts", response_model=TaskArtifactsResponse)
async def get_task_artifacts(
    task_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Return all stored test files for a task from Postgres.

    Это позволяет открывать задачу и видеть тесты с любого устройства,
    даже если Celery-результат уже недоступен.
    """
    record = db.get(TaskRecord, task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")

    artifacts = (
        db.query(TaskArtifact)
        .filter(TaskArtifact.task_id == task_id)
        .order_by(TaskArtifact.id)
        .all()
    )

    files: List[TaskFile] = [
        TaskFile(filename=a.filename, description=a.description, content=a.content)
        for a in artifacts
    ]

    return TaskArtifactsResponse(
        task_id=task_id,
        test_type=record.test_type,
        priority=record.priority,
        feature=record.feature,
        files=files,
    )




