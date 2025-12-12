"""Pydantic models for GitLab integration requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class GitLabGenerateRequest(BaseModel):
    """Request model for generating and committing tests."""

    gitlab_url: str = Field(..., description="Full GitLab project URL")
    spec_path: str = Field(..., description="Path to specification file in repository")
    test_type: str = Field(default="api", description="Type of tests: api, ui, manual")
    branch: Optional[str] = Field(None, description="Branch name (auto-generated if not provided)")
    target_branch: Optional[str] = Field(None, description="Target branch for MR (defaults to main)")
    create_mr: bool = Field(True, description="Whether to create Merge Request")
    private_token: str = Field(..., description="GitLab personal access token")
    gitlab_base_url: Optional[str] = Field(None, description="GitLab API base URL (optional)")
    user_email: Optional[str] = Field(None, description="User email for commit author")
    user_name: Optional[str] = Field(None, description="User name for commit author")
    commit_message: Optional[str] = Field(None, description="Custom commit message (optional)")


class GitLabGenerateResponse(BaseModel):
    """Response model for generate and commit operation."""

    success: bool
    merge_request_url: Optional[str] = None
    branch: str
    commit_id: Optional[str] = None
    generated_files: List[str]
    coverage_summary: Dict[str, Any]


class GitLabValidateRequest(BaseModel):
    """Request model for validating GitLab token."""

    private_token: str
    gitlab_base_url: Optional[str] = None


class GitLabValidateResponse(BaseModel):
    """Response model for token validation."""

    valid: bool
    user_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None



