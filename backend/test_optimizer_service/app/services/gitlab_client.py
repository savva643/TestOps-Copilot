"""GitLab API client for fetching repository code."""

from typing import Dict, Any, List, Optional
import httpx
import structlog
import tempfile
import os
from pathlib import Path

logger = structlog.get_logger()


class GitLabClient:
    """Client for interacting with GitLab API."""

    def __init__(self, gitlab_url: str, access_token: str):
        """
        Initialize GitLab client.

        Args:
            gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
            access_token: GitLab personal access token or OAuth token
        """
        self.base_url = gitlab_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v4"
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get project information.

        Args:
            project_id: Project ID or path (e.g., "group/project")

        Returns:
            Project information
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # URL encode project path
            encoded_id = project_id.replace("/", "%2F")
            resp = await client.get(
                f"{self.api_url}/projects/{encoded_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_file_content(
        self, project_id: str, file_path: str, ref: str = "main"
    ) -> str:
        """
        Get file content from repository.

        Args:
            project_id: Project ID or path
            file_path: Path to file in repository
            ref: Branch or commit SHA

        Returns:
            File content as string
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            encoded_id = project_id.replace("/", "%2F")
            encoded_path = file_path.replace("/", "%2F")
            resp = await client.get(
                f"{self.api_url}/projects/{encoded_id}/repository/files/{encoded_path}/raw",
                headers=self.headers,
                params={"ref": ref},
            )
            resp.raise_for_status()
            return resp.text

    async def get_tree(
        self,
        project_id: str,
        path: str = "",
        ref: str = "main",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get repository tree (list of files).

        Args:
            project_id: Project ID or path
            path: Path in repository
            ref: Branch or commit SHA
            recursive: Whether to get files recursively

        Returns:
            List of files and directories
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            encoded_id = project_id.replace("/", "%2F")
            params = {"ref": ref, "recursive": "true" if recursive else "false"}
            if path:
                params["path"] = path

            resp = await client.get(
                f"{self.api_url}/projects/{encoded_id}/repository/tree",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def clone_repository(
        self, project_id: str, ref: str = "main", target_dir: Optional[str] = None
    ) -> str:
        """
        Clone repository to temporary directory.

        Args:
            project_id: Project ID or path
            ref: Branch or commit SHA
            target_dir: Target directory (if None, creates temp directory)

        Returns:
            Path to cloned repository
        """
        project_info = await self.get_project(project_id)
        repo_url = project_info.get("http_url_to_repo") or project_info.get("ssh_url_to_repo")

        if not repo_url:
            raise ValueError("Repository URL not found in project info")

        # Add token to URL for authentication
        if "http" in repo_url:
            # For HTTP URLs, embed token
            if "@" not in repo_url:
                # Format: https://oauth2:TOKEN@gitlab.com/group/project.git
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(repo_url)
                netloc = f"oauth2:{self.access_token}@{parsed.netloc}"
                repo_url = urlunparse(
                    (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
                )

        if target_dir is None:
            target_dir = tempfile.mkdtemp()

        # Use GitPython to clone
        try:
            from git import Repo

            repo = Repo.clone_from(repo_url, target_dir, depth=1, branch=ref)
            logger.info("Repository cloned", project_id=project_id, ref=ref, path=target_dir)
            return target_dir
        except Exception as e:
            logger.error("Failed to clone repository", error=str(e), exc_info=True)
            raise

    async def get_test_files(
        self, project_id: str, test_directory: str = "tests", ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """
        Get list of test files from repository.

        Args:
            project_id: Project ID or path
            test_directory: Directory containing tests
            ref: Branch or commit SHA

        Returns:
            List of test files with their paths
        """
        tree = await self.get_tree(project_id, path=test_directory, ref=ref, recursive=True)
        test_files = [
            item
            for item in tree
            if item.get("type") == "blob"
            and (
                item.get("path", "").endswith("_test.py")
                or item.get("path", "").endswith("test_.py")
                or item.get("path", "").startswith("test_")
                or "test" in item.get("path", "").lower()
            )
        ]
        logger.info("Test files found", count=len(test_files), project_id=project_id)
        return test_files

