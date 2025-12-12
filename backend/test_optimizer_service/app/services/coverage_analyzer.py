"""Coverage analyzer service."""

from typing import Dict, Any, List, Optional
import structlog
import tempfile
import os
from pathlib import Path

from app.services.gitlab_client import GitLabClient
from app.services.ast_analyzer import ASTAnalyzer

logger = structlog.get_logger()


class CoverageAnalyzer:
    """Analyzes test coverage for a repository."""

    async def analyze(
        self,
        git_repo_url: str = None,
        gitlab_project_id: str = None,
        gitlab_token: str = None,
        gitlab_url: str = None,
        branch: str = "main",
        test_directory: str = "tests",
        api_spec_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze test coverage.

        Args:
            git_repo_url: URL of Git repository (legacy, use gitlab_project_id)
            gitlab_project_id: GitLab project ID or path (e.g., "group/project")
            gitlab_token: GitLab access token
            gitlab_url: GitLab instance URL (defaults to gitlab.com)
            branch: Branch to analyze
            test_directory: Directory containing tests
            api_spec_path: Optional path to OpenAPI spec for endpoint comparison

        Returns:
            Coverage analysis results
        """
        try:
            tmpdir = None
            if gitlab_project_id and gitlab_token:
                # Use GitLab API
                gitlab_url = gitlab_url or "https://gitlab.com"
                client = GitLabClient(gitlab_url, gitlab_token)
                tmpdir = await client.clone_repository(gitlab_project_id, ref=branch)
            elif git_repo_url:
                # Fallback to direct git clone
                from git import Repo

                tmpdir = tempfile.mkdtemp()
                repo = Repo.clone_from(git_repo_url, tmpdir)
                repo.git.checkout(branch)
            else:
                raise ValueError("Either gitlab_project_id+gitlab_token or git_repo_url must be provided")

            # Analyze test files
            ast_analyzer = ASTAnalyzer()
            test_dir = os.path.join(tmpdir, test_directory)
            if not os.path.exists(test_dir):
                # Try to find test directory
                for root, dirs, files in os.walk(tmpdir):
                    if "test" in root.lower() or any("test" in f for f in files if f.endswith(".py")):
                        test_dir = root
                        break

            if not os.path.exists(test_dir):
                logger.warning("Test directory not found", test_directory=test_directory, repo_path=tmpdir)
                return {
                    "coverage_percentage": 0.0,
                    "covered_endpoints": [],
                    "uncovered_endpoints": [],
                    "recommendations": ["Test directory not found"],
                    "test_files_analyzed": 0,
                }

            analysis = ast_analyzer.analyze_directory(test_dir)

            # Extract endpoints from API spec if provided
            all_endpoints = set()
            if api_spec_path:
                all_endpoints = await self._extract_endpoints_from_spec(
                    os.path.join(tmpdir, api_spec_path)
                )

            # If no spec provided, try to infer from codebase
            if not all_endpoints:
                all_endpoints = await self._extract_endpoints_from_codebase(tmpdir)

            covered_endpoints = set(analysis.get("endpoints_tested", []))
            uncovered_endpoints = all_endpoints - covered_endpoints

            coverage_percentage = (
                (len(covered_endpoints) / len(all_endpoints) * 100)
                if all_endpoints
                else 0.0
            )

            recommendations = []
            if uncovered_endpoints:
                recommendations.append(
                    f"Add tests for {len(uncovered_endpoints)} uncovered endpoints"
                )
                # List top 5 uncovered endpoints
                top_uncovered = list(uncovered_endpoints)[:5]
                recommendations.append(f"Priority endpoints: {', '.join(top_uncovered)}")
            else:
                recommendations.append("All endpoints are covered by tests")

            if analysis.get("total_test_functions", 0) == 0:
                recommendations.append("No test functions found in the repository")

            result = {
                "coverage_percentage": round(coverage_percentage, 2),
                "covered_endpoints": sorted(list(covered_endpoints)),
                "uncovered_endpoints": sorted(list(uncovered_endpoints)),
                "recommendations": recommendations,
                "test_files_analyzed": analysis.get("files_analyzed", 0),
                "total_test_functions": analysis.get("total_test_functions", 0),
                "total_endpoints": len(all_endpoints),
            }

            logger.info(
                "Coverage analysis completed",
                coverage=result["coverage_percentage"],
                test_files=result["test_files_analyzed"],
            )

            return result

        except Exception as e:
            logger.error("Failed to analyze coverage", error=str(e), exc_info=True)
            raise

    async def _extract_endpoints_from_spec(self, spec_path: str) -> set:
        """Extract endpoints from OpenAPI spec."""
        try:
            import yaml
            import json

            with open(spec_path, "r", encoding="utf-8") as f:
                if spec_path.endswith(".yaml") or spec_path.endswith(".yml"):
                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)

            endpoints = set()
            paths = spec.get("paths", {})
            for path, methods in paths.items():
                endpoints.add(path)
                # Also add method-specific paths if needed
                for method in methods.keys():
                    if method in ["get", "post", "put", "delete", "patch"]:
                        endpoints.add(f"{method.upper()} {path}")

            return endpoints
        except Exception as e:
            logger.warning("Failed to extract endpoints from spec", error=str(e))
            return set()

    async def _extract_endpoints_from_codebase(self, codebase_path: str) -> set:
        """Try to extract endpoints from codebase (FastAPI routes, etc.)."""
        endpoints = set()
        for root, dirs, files in os.walk(codebase_path):
            # Skip test directories
            if "test" in root.lower():
                continue

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Look for FastAPI route decorators
                            import re

                            # Pattern: @router.get("/path") or @app.get("/path")
                            patterns = [
                                r'@\w+\.(get|post|put|delete|patch)\("([^"]+)"',
                                r'@\w+\.route\("([^"]+)"',
                            ]
                            for pattern in patterns:
                                matches = re.findall(pattern, content)
                                for match in matches:
                                    if isinstance(match, tuple):
                                        endpoint = match[-1] if match else ""
                                    else:
                                        endpoint = match
                                    if endpoint:
                                        endpoints.add(endpoint)
                    except Exception:
                        pass

        return endpoints

