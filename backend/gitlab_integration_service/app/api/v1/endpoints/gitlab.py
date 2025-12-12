"""GitLab integration endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from app.models.gitlab_models import (
    GitLabGenerateRequest,
    GitLabGenerateResponse,
    GitLabValidateRequest,
    GitLabValidateResponse,
)
from app.services.gitlab_client import GitLabClient
from app.services.integration_service import GitLabIntegrationService
from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter()


@router.post("/validate", response_model=GitLabValidateResponse)
async def validate_gitlab_token(request: GitLabValidateRequest):
    """
    Validate GitLab token and return user information.

    This endpoint checks if the provided token is valid and has necessary permissions.
    """
    try:
        base_url = request.gitlab_base_url or settings.GITLAB_BASE_URL
        client = GitLabClient(base_url, request.private_token)

        user_info = await client.validate_token()

        return GitLabValidateResponse(
            valid=True,
            user_info={
                "id": user_info.get("id"),
                "username": user_info.get("username"),
                "name": user_info.get("name"),
                "email": user_info.get("email"),
            },
        )
    except Exception as e:
        logger.error("Token validation failed", error=str(e))
        return GitLabValidateResponse(valid=False, error=str(e))


@router.post("/generate-and-commit", response_model=GitLabGenerateResponse)
async def generate_and_commit_tests(request: GitLabGenerateRequest):
    """
    Main endpoint: Generate tests from specification and commit to GitLab.

    Workflow:
    1. Download specification file from GitLab repository
    2. Parse specification via spec-parser-service
    3. Generate tests via code-generator-service
    4. Create branch and commit tests to GitLab
    5. Create Merge Request (if requested)

    Returns:
        Information about created MR, branch, and generated files
    """
    try:
        # Initialize GitLab client
        base_url = request.gitlab_base_url or settings.GITLAB_BASE_URL
        client = GitLabClient(base_url, request.private_token)

        # Initialize integration service
        integration_service = GitLabIntegrationService(client)

        # Prepare user data for commit author
        user_data = None
        if request.user_email or request.user_name:
            user_data = {}
            if request.user_email:
                user_data["email"] = request.user_email
            if request.user_name:
                user_data["name"] = request.user_name

        # Execute workflow
        result = await integration_service.generate_and_commit_tests(
            project_url=request.gitlab_url,
            spec_path=request.spec_path,
            test_type=request.test_type,
            branch=request.branch,
            target_branch=request.target_branch,
            create_mr=request.create_mr,
            user_data=user_data,
        )

        return GitLabGenerateResponse(**result)

    except FileNotFoundError as e:
        logger.error("Specification file not found", error=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error("Validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to generate and commit tests", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/project/{project_path:path}/tree")
async def get_repository_tree(
    project_path: str,
    path: str = "",
    ref: str = "main",
    recursive: bool = True,
    private_token: str = "",
    gitlab_base_url: str = None,
):
    """
    Get repository tree (list of files).

    This endpoint helps users browse repository structure to find specification files.
    """
    try:
        if not private_token:
            raise HTTPException(status_code=401, detail="GitLab token required")

        base_url = gitlab_base_url or settings.GITLAB_BASE_URL
        client = GitLabClient(base_url, private_token)

        tree = await client.get_repository_tree(
            project_id=project_path, path=path, ref=ref, recursive=recursive
        )

        return {"files": tree}
    except Exception as e:
        logger.error("Failed to get repository tree", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))




