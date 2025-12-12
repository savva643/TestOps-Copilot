"""Test optimizer endpoints."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

from app.services.coverage_analyzer import CoverageAnalyzer
from app.services.duplicate_finder import DuplicateFinder

logger = structlog.get_logger()

router = APIRouter()


class AnalyzeCoverageRequest(BaseModel):
    """Request model for coverage analysis."""

    git_repo_url: Optional[str] = None
    gitlab_project_id: Optional[str] = None
    gitlab_url: Optional[str] = None
    branch: str = "main"
    test_directory: str = "tests"
    api_spec_path: Optional[str] = None


class CoverageAnalysisResponse(BaseModel):
    """Response model for coverage analysis."""

    coverage_percentage: float
    covered_endpoints: List[str]
    uncovered_endpoints: List[str]
    recommendations: List[str]
    test_files_analyzed: int = 0
    total_test_functions: int = 0
    total_endpoints: int = 0


class FindDuplicatesRequest(BaseModel):
    """Request model for duplicate finding."""

    git_repo_url: Optional[str] = None
    gitlab_project_id: Optional[str] = None
    gitlab_url: Optional[str] = None
    branch: str = "main"
    test_directory: str = "tests"
    similarity_threshold: float = 0.8


class DuplicatesResponse(BaseModel):
    """Response model for duplicates."""

    duplicates: List[Dict[str, Any]]
    total_tests: int
    duplicate_count: int


class OptimizationRecommendationsResponse(BaseModel):
    """Response model for optimization recommendations."""

    recommendations: List[Dict[str, Any]]
    performance_issues: List[Dict[str, Any]]
    best_practices: List[Dict[str, Any]]


@router.post("/coverage", response_model=CoverageAnalysisResponse)
async def analyze_coverage(
    request: AnalyzeCoverageRequest,
    x_gitlab_token: Optional[str] = Header(None, alias="X-GitLab-Token"),
):
    """
    Analyze test coverage for a Git repository.

    Supports both GitLab API (via gitlab_project_id + X-GitLab-Token header)
    and direct git clone (via git_repo_url).
    """
    try:
        analyzer = CoverageAnalyzer()
        gitlab_token = x_gitlab_token or request.gitlab_project_id  # Fallback for testing

        result = await analyzer.analyze(
            git_repo_url=request.git_repo_url,
            gitlab_project_id=request.gitlab_project_id,
            gitlab_token=gitlab_token,
            gitlab_url=request.gitlab_url,
            branch=request.branch,
            test_directory=request.test_directory,
            api_spec_path=request.api_spec_path,
        )

        return CoverageAnalysisResponse(**result)
    except Exception as e:
        logger.error("Failed to analyze coverage", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duplicates", response_model=DuplicatesResponse)
async def find_duplicates(
    request: FindDuplicatesRequest,
    x_gitlab_token: Optional[str] = Header(None, alias="X-GitLab-Token"),
):
    """
    Find duplicate tests in a Git repository.

    Supports both GitLab API (via gitlab_project_id + X-GitLab-Token header)
    and direct git clone (via git_repo_url).
    """
    try:
        finder = DuplicateFinder()
        gitlab_token = x_gitlab_token or request.gitlab_project_id  # Fallback for testing

        result = await finder.find(
            git_repo_url=request.git_repo_url,
            gitlab_project_id=request.gitlab_project_id,
            gitlab_token=gitlab_token,
            gitlab_url=request.gitlab_url,
            branch=request.branch,
            test_directory=request.test_directory,
            similarity_threshold=request.similarity_threshold,
        )

        return DuplicatesResponse(**result)
    except Exception as e:
        logger.error("Failed to find duplicates", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=OptimizationRecommendationsResponse)
async def get_optimization_recommendations(
    request: AnalyzeCoverageRequest,
    x_gitlab_token: Optional[str] = Header(None, alias="X-GitLab-Token"),
):
    """
    Get optimization recommendations for test suite.

    Combines coverage analysis and duplicate detection to provide recommendations.
    """
    try:
        gitlab_token = x_gitlab_token or request.gitlab_project_id

        # Run both analyses
        analyzer = CoverageAnalyzer()
        finder = DuplicateFinder()

        coverage_result = await analyzer.analyze(
            git_repo_url=request.git_repo_url,
            gitlab_project_id=request.gitlab_project_id,
            gitlab_token=gitlab_token,
            gitlab_url=request.gitlab_url,
            branch=request.branch,
            test_directory=request.test_directory,
            api_spec_path=request.api_spec_path,
        )

        duplicates_result = await finder.find(
            git_repo_url=request.git_repo_url,
            gitlab_project_id=request.gitlab_project_id,
            gitlab_token=gitlab_token,
            gitlab_url=request.gitlab_url,
            branch=request.branch,
            test_directory=request.test_directory,
        )

        # Generate recommendations
        recommendations = []
        performance_issues = []
        best_practices = []

        # Coverage recommendations
        if coverage_result["coverage_percentage"] < 70:
            recommendations.append(
                {
                    "type": "coverage",
                    "priority": "high",
                    "message": f"Test coverage is {coverage_result['coverage_percentage']}%. Aim for at least 70%.",
                    "action": "Add tests for uncovered endpoints",
                }
            )

        if coverage_result["uncovered_endpoints"]:
            top_uncovered = coverage_result["uncovered_endpoints"][:5]
            recommendations.append(
                {
                    "type": "coverage",
                    "priority": "medium",
                    "message": f"Found {len(coverage_result['uncovered_endpoints'])} uncovered endpoints",
                    "action": f"Add tests for: {', '.join(top_uncovered)}",
                }
            )

        # Duplicate recommendations
        if duplicates_result["duplicate_count"] > 0:
            recommendations.append(
                {
                    "type": "duplicates",
                    "priority": "medium",
                    "message": f"Found {duplicates_result['duplicate_count']} duplicate test pairs",
                    "action": "Consider consolidating duplicate tests to reduce maintenance burden",
                }
            )

        # Performance recommendations
        if coverage_result["total_test_functions"] > 1000:
            performance_issues.append(
                {
                    "type": "performance",
                    "message": "Large number of test functions may slow down test execution",
                    "suggestion": "Consider splitting tests into multiple suites or using test parallelization",
                }
            )

        # Best practices
        if coverage_result["test_files_analyzed"] > 0:
            best_practices.append(
                {
                    "type": "best_practice",
                    "message": "Use test fixtures and parametrization to reduce code duplication",
                }
            )
            best_practices.append(
                {
                    "type": "best_practice",
                    "message": "Ensure tests are independent and can run in any order",
                }
            )

        return OptimizationRecommendationsResponse(
            recommendations=recommendations,
            performance_issues=performance_issues,
            best_practices=best_practices,
        )

    except Exception as e:
        logger.error("Failed to get optimization recommendations", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

