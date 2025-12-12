"""Duplicate test finder service."""

from typing import Dict, Any, List, Tuple
import structlog
import tempfile
import hashlib
import os
from pathlib import Path
import difflib

from app.services.gitlab_client import GitLabClient
from app.services.ast_analyzer import ASTAnalyzer

logger = structlog.get_logger()


class DuplicateFinder:
    """Finds duplicate tests in a repository."""

    async def find(
        self,
        git_repo_url: str = None,
        gitlab_project_id: str = None,
        gitlab_token: str = None,
        gitlab_url: str = None,
        branch: str = "main",
        test_directory: str = "tests",
        similarity_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Find duplicate tests.

        Args:
            git_repo_url: URL of Git repository (legacy, use gitlab_project_id)
            gitlab_project_id: GitLab project ID or path
            gitlab_token: GitLab access token
            gitlab_url: GitLab instance URL
            branch: Branch to analyze
            test_directory: Directory containing tests
            similarity_threshold: Minimum similarity to consider tests duplicates (0.0-1.0)

        Returns:
            Duplicate test results
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

            # Find all test files
            test_dir = os.path.join(tmpdir, test_directory)
            if not os.path.exists(test_dir):
                # Try to find test directory
                for root, dirs, files in os.walk(tmpdir):
                    if "test" in root.lower() or any("test" in f for f in files if f.endswith(".py")):
                        test_dir = root
                        break

            if not os.path.exists(test_dir):
                logger.warning("Test directory not found", test_directory=test_directory)
                return {
                    "duplicates": [],
                    "total_tests": 0,
                    "duplicate_count": 0,
                }

            # Get all test files
            test_files = []
            for path in Path(test_dir).rglob("*.py"):
                if "test" in path.name.lower():
                    test_files.append(str(path))

            # Analyze each test file
            ast_analyzer = ASTAnalyzer()
            test_functions = []

            for file_path in test_files:
                try:
                    result = ast_analyzer.analyze_file(file_path)
                    for func in result.get("test_functions", []):
                        func["file"] = file_path
                        func["content"] = self._get_function_content(file_path, func["name"], func["line"])
                        test_functions.append(func)
                except Exception as e:
                    logger.warning("Failed to analyze file", file=file_path, error=str(e))

            # Find duplicates using multiple methods
            duplicates = []
            total_tests = len(test_functions)

            # Method 1: Hash-based exact duplicates
            hash_map = {}
            for func in test_functions:
                content_hash = hashlib.md5(func["content"].encode()).hexdigest()
                if content_hash in hash_map:
                    duplicates.append(
                        {
                            "test1": f"{func['file']}::{func['name']}",
                            "test2": f"{hash_map[content_hash]['file']}::{hash_map[content_hash]['name']}",
                            "similarity": 1.0,
                            "method": "exact_hash",
                        }
                    )
                else:
                    hash_map[content_hash] = func

            # Method 2: Semantic similarity (name-based)
            name_groups = {}
            for func in test_functions:
                # Normalize test name (remove test_ prefix, etc.)
                normalized = func["name"].lower().replace("test_", "").replace("_", "")
                if normalized not in name_groups:
                    name_groups[normalized] = []
                name_groups[normalized].append(func)

            for normalized_name, funcs in name_groups.items():
                if len(funcs) > 1:
                    # Compare all pairs
                    for i, func1 in enumerate(funcs):
                        for func2 in funcs[i + 1 :]:
                            similarity = self._calculate_similarity(func1["content"], func2["content"])
                            if similarity >= similarity_threshold:
                                duplicates.append(
                                    {
                                        "test1": f"{func1['file']}::{func1['name']}",
                                        "test2": f"{func2['file']}::{func2['name']}",
                                        "similarity": round(similarity, 2),
                                        "method": "semantic",
                                    }
                                )

            # Method 3: Content-based similarity
            for i, func1 in enumerate(test_functions):
                for func2 in test_functions[i + 1 :]:
                    # Skip if already found as duplicate
                    if any(
                        d["test1"] == f"{func1['file']}::{func1['name']}"
                        and d["test2"] == f"{func2['file']}::{func2['name']}"
                        for d in duplicates
                    ):
                        continue

                    similarity = self._calculate_similarity(func1["content"], func2["content"])
                    if similarity >= similarity_threshold:
                        duplicates.append(
                            {
                                "test1": f"{func1['file']}::{func1['name']}",
                                "test2": f"{func2['file']}::{func2['name']}",
                                "similarity": round(similarity, 2),
                                "method": "content",
                            }
                        )

            # Remove exact duplicates from results
            seen = set()
            unique_duplicates = []
            for dup in duplicates:
                key = tuple(sorted([dup["test1"], dup["test2"]]))
                if key not in seen:
                    seen.add(key)
                    unique_duplicates.append(dup)

            result = {
                "duplicates": unique_duplicates,
                "total_tests": total_tests,
                "duplicate_count": len(unique_duplicates),
            }

            logger.info(
                "Duplicate analysis completed",
                duplicates=result["duplicate_count"],
                total_tests=total_tests,
            )

            return result

        except Exception as e:
            logger.error("Failed to find duplicates", error=str(e), exc_info=True)
            raise

    def _get_function_content(self, file_path: str, function_name: str, start_line: int) -> str:
        """Extract function content from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Find function start and end
                content_lines = []
                indent_level = None
                in_function = False

                for i, line in enumerate(lines[start_line - 1 :], start=start_line):
                    if i == start_line:
                        in_function = True
                        indent_level = len(line) - len(line.lstrip())
                        content_lines.append(line.rstrip())
                    elif in_function:
                        current_indent = len(line) - len(line.lstrip())
                        if line.strip() and current_indent <= indent_level and not line.strip().startswith("#"):
                            break
                        content_lines.append(line.rstrip())

                return "\n".join(content_lines)
        except Exception as e:
            logger.warning("Failed to extract function content", file=file_path, error=str(e))
            return ""

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two test functions."""
        if not content1 or not content2:
            return 0.0

        # Normalize content (remove whitespace, comments)
        def normalize(text: str) -> str:
            lines = text.split("\n")
            normalized = []
            for line in lines:
                # Remove comments
                if "#" in line:
                    line = line[: line.index("#")]
                # Remove leading/trailing whitespace
                line = line.strip()
                if line:
                    normalized.append(line)
            return " ".join(normalized)

        norm1 = normalize(content1)
        norm2 = normalize(content2)

        if not norm1 or not norm2:
            return 0.0

        # Use SequenceMatcher for similarity
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        return similarity

