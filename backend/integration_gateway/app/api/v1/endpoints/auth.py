"""Auth endpoints for obtaining Cloud.ru IAM tokens and GitLab integration via gateway."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


class TokenRequest(BaseModel):
    keyId: str
    secret: str
    llmApiKey: str | None = None


class GitLabTokenRequest(BaseModel):
    """Request to store GitLab token."""

    gitlab_token: str
    gitlab_url: Optional[str] = None


@router.post("/auth/token")
async def get_iam_token(payload: TokenRequest):
    """
    Proxy to Cloud.ru IAM to obtain access token.

    The token is returned as-is from IAM API.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                settings.IAM_AUTH_URL,
                json={"keyId": payload.keyId, "secret": payload.secret},
                headers={"Content-Type": "application/json"},
            )
        resp.raise_for_status()
        data = resp.json()
        logger.info("IAM token issued", has_token=bool(data.get("access_token")))
        return data
    except httpx.HTTPStatusError as e:
        detail = e.response.text
        logger.error("IAM token request failed", status=e.response.status_code, detail=detail)
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except Exception as e:
        logger.error("Unexpected error requesting IAM token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to obtain IAM token")


@router.post("/auth/gitlab/token")
async def store_gitlab_token(payload: GitLabTokenRequest):
    """
    Store GitLab token for later use.

    In production, this should store tokens securely (e.g., in database with encryption).
    For now, this is a placeholder that validates the token.
    """
    try:
        gitlab_url = payload.gitlab_url or settings.GITLAB_URL
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Validate token by making a test request
            resp = await client.get(
                f"{gitlab_url}/user",
                headers={"Authorization": f"Bearer {payload.gitlab_token}"},
            )
            resp.raise_for_status()
            user_data = resp.json()
            logger.info("GitLab token validated", username=user_data.get("username"))
            return {
                "status": "success",
                "message": "GitLab token validated and stored",
                "user": user_data.get("username"),
            }
    except httpx.HTTPStatusError as e:
        logger.error("GitLab token validation failed", status=e.response.status_code)
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Invalid GitLab token or unable to connect to GitLab",
        )
    except Exception as e:
        logger.error("Unexpected error validating GitLab token", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate GitLab token")


@router.get("/gitlab/projects")
async def get_gitlab_projects(
    gitlab_token: str = Header(..., alias="X-GitLab-Token"),
    gitlab_url: Optional[str] = Header(None, alias="X-GitLab-URL"),
):
    """
    Get list of GitLab projects accessible with the provided token.

    Requires Bearer token in X-GitLab-Token header.
    """
    try:
        base_url = gitlab_url or settings.GITLAB_URL
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{base_url}/projects",
                headers={"Authorization": f"Bearer {gitlab_token}"},
                params={"per_page": 100, "simple": True},
            )
            resp.raise_for_status()
            projects = resp.json()
            logger.info("GitLab projects retrieved", count=len(projects))
            return {"projects": projects}
    except httpx.HTTPStatusError as e:
        logger.error("Failed to get GitLab projects", status=e.response.status_code)
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Failed to retrieve GitLab projects",
        )
    except Exception as e:
        logger.error("Unexpected error getting GitLab projects", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get GitLab projects")

