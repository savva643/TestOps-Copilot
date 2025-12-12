"""GitLab task endpoints for saving GitLab integration tasks to history."""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import structlog

from app.core.security import verify_api_key
from app.db import get_db
from app.models import TaskRecord
from sqlalchemy.orm import Session

logger = structlog.get_logger()

router = APIRouter()


class GitLabTaskRequest(BaseModel):
    """Request model for creating GitLab task record."""

    gitlab_url: str
    spec_path: str
    test_type: str
    merge_request_url: Optional[str] = None
    branch: Optional[str] = None
    generated_files: Optional[List[str]] = None
    coverage_summary: Optional[Dict[str, Any]] = None


@router.post("/task")
async def create_gitlab_task(
    request: GitLabTaskRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Create a task record for GitLab integration workflow.
    
    This endpoint saves GitLab tasks to the database so they appear
    in the task history alongside regular generation tasks.
    """
    try:
        requester_id = http_request.headers.get("X-Key-Id")
        
        # Generate unique task ID
        task_id = f"gitlab-{uuid.uuid4().hex[:12]}"
        
        # Create description from GitLab info
        description = f"GitLab: {request.gitlab_url}\nSpec: {request.spec_path}\nType: {request.test_type}"
        if request.branch:
            description += f"\nBranch: {request.branch}"
        
        # Create result summary
        result_summary_parts = []
        if request.merge_request_url:
            result_summary_parts.append(f"MR: {request.merge_request_url}")
        if request.generated_files:
            result_summary_parts.append(f"Files: {len(request.generated_files)}")
        if request.coverage_summary:
            result_summary_parts.append(f"Coverage: {request.coverage_summary.get('endpoints_covered', 0)} endpoints")
        
        result_summary = " | ".join(result_summary_parts) if result_summary_parts else "GitLab task completed"
        
        # Create or update task record
        existing = db.get(TaskRecord, task_id)
        if existing:
            existing.update_status(
                status="completed",
                progress_message=f"GitLab task completed. MR: {request.merge_request_url or 'N/A'}",
                result_summary=result_summary,
            )
            existing.gitlab_url = request.gitlab_url
            existing.gitlab_merge_request_url = request.merge_request_url
            existing.gitlab_branch = request.branch
            existing.gitlab_spec_path = request.spec_path
            existing.is_gitlab_task = "true"
        else:
            task_record = TaskRecord(
                task_id=task_id,
                status="completed",
                description=description,
                test_type=request.test_type,
                owner_id=requester_id,
                gitlab_url=request.gitlab_url,
                gitlab_merge_request_url=request.merge_request_url,
                gitlab_branch=request.branch,
                gitlab_spec_path=request.spec_path,
                is_gitlab_task="true",
                progress_message=f"GitLab task completed. MR: {request.merge_request_url or 'N/A'}",
                result_summary=result_summary,
            )
            db.add(task_record)
        
        db.commit()
        
        logger.info(
            "GitLab task created",
            task_id=task_id,
            gitlab_url=request.gitlab_url,
            merge_request_url=request.merge_request_url,
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "GitLab task saved to history",
        }
        
    except Exception as e:
        logger.error("Failed to create GitLab task", error=str(e), exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save GitLab task: {str(e)}")



