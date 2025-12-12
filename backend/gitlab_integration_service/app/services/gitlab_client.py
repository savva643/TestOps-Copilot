"""GitLab API client for repository operations."""

from typing import Dict, Any, List, Optional
import httpx
import structlog
from urllib.parse import quote

logger = structlog.get_logger()


class GitLabClient:
    """Client for interacting with GitLab API v4."""

    def __init__(self, base_url: str, private_token: str):
        """
        Initialize GitLab client.

        Args:
            base_url: GitLab instance URL (e.g., https://gitlab.com/api/v4)
            private_token: GitLab personal access token or project access token
        """
        self.base_url = base_url.rstrip("/")
        self.token = private_token
        self.headers = {
            "Authorization": f"Bearer {private_token}",
            "Content-Type": "application/json",
        }

    def _get_project_id(self, project_path: str) -> str:
        """
        Encode project path for URL.

        Args:
            project_path: Project path like "group/project" or "group%2Fproject"

        Returns:
            URL-encoded project ID
        """
        # If already encoded, return as is
        if "%2F" in project_path or "%2f" in project_path:
            return project_path
        # Otherwise encode it
        return quote(project_path, safe="")

    async def get_file_content(
        self, project_id: str, file_path: str, ref: str = "main"
    ) -> str:
        """
        Get file content from repository.

        Args:
            project_id: Project ID or path (e.g., "group/project")
            file_path: Path to file in repository
            ref: Branch or commit SHA

        Returns:
            File content as string
        """
        encoded_id = self._get_project_id(project_id)
        encoded_path = quote(file_path, safe="")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/projects/{encoded_id}/repository/files/{encoded_path}/raw",
                    headers=self.headers,
                    params={"ref": ref},
                )
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.error(
                        "File not found",
                        project_id=project_id,
                        file_path=file_path,
                        ref=ref,
                    )
                    raise FileNotFoundError(
                        f"File {file_path} not found in project {project_id} at ref {ref}"
                    )
                raise

    async def create_branch(
        self, project_id: str, branch: str, ref: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a new branch.

        Args:
            project_id: Project ID or path
            branch: Name of new branch
            ref: Source branch or commit SHA

        Returns:
            Branch information
        """
        encoded_id = self._get_project_id(project_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/projects/{encoded_id}/repository/branches",
                    headers=self.headers,
                    json={"branch": branch, "ref": ref},
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    # Branch might already exist, try to get it
                    logger.warning("Branch might already exist", branch=branch)
                    return await self.get_branch(project_id, branch)
                raise

    async def get_branch(self, project_id: str, branch: str) -> Dict[str, Any]:
        """
        Get branch information.

        Args:
            project_id: Project ID or path
            branch: Branch name

        Returns:
            Branch information
        """
        encoded_id = self._get_project_id(project_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/projects/{encoded_id}/repository/branches/{quote(branch)}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_commit(
        self,
        project_id: str,
        branch: str,
        commit_message: str,
        actions: List[Dict[str, str]],
        author_email: Optional[str] = None,
        author_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a commit with multiple file changes.

        Args:
            project_id: Project ID or path
            branch: Target branch
            commit_message: Commit message
            actions: List of file actions, e.g.:
                [
                    {"action": "create", "file_path": "tests/test.py", "content": "..."},
                    {"action": "update", "file_path": "tests/test2.py", "content": "..."},
                ]
            author_email: Optional author email
            author_name: Optional author name

        Returns:
            Commit information
        """
        encoded_id = self._get_project_id(project_id)

        payload = {
            "branch": branch,
            "commit_message": commit_message,
            "actions": actions,
        }

        if author_email and author_name:
            payload["author_email"] = author_email
            payload["author_name"] = author_name

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/projects/{encoded_id}/repository/commits",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_merge_request(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Create a Merge Request.

        Args:
            project_id: Project ID or path
            source_branch: Source branch name
            target_branch: Target branch name (usually "main" or "develop")
            title: MR title
            description: MR description

        Returns:
            Merge Request information
        """
        encoded_id = self._get_project_id(project_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/projects/{encoded_id}/merge_requests",
                headers=self.headers,
                json={
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "title": title,
                    "description": description,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_repository_tree(
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
        encoded_id = self._get_project_id(project_id)

        params = {"ref": ref, "recursive": "true" if recursive else "false"}
        if path:
            params["path"] = path

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/projects/{encoded_id}/repository/tree",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get project information.

        Args:
            project_id: Project ID or path

        Returns:
            Project information
        """
        encoded_id = self._get_project_id(project_id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/projects/{encoded_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def validate_token(self) -> Dict[str, Any]:
        """
        Validate GitLab token by getting current user info.

        Returns:
            User information if token is valid
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/user",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()



