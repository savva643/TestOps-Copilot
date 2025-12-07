"""Test optimizer endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import structlog

from app.services.coverage_analyzer import CoverageAnalyzer
from app.services.duplicate_finder import DuplicateFinder

logger = structlog.get_logger()

router = APIRouter()


class AnalyzeCoverageRequest(BaseModel):
    """Request model for coverage analysis."""

    git_repo_url: str
    branch: str = "main"
    test_directory: str = "tests"


class CoverageAnalysisResponse(BaseModel):
    """Response model for coverage analysis."""

    coverage_percentage: float
    covered_endpoints: List[str]
    uncovered_endpoints: List[str]
    recommendations: List[str]


class FindDuplicatesRequest(BaseModel):
    """Request model for duplicate finding."""

    git_repo_url: str
    branch: str = "main"
    test_directory: str = "tests"


class DuplicatesResponse(BaseModel):
    """Response model for duplicates."""

    duplicates: List[Dict[str, Any]]
    total_tests: int
    duplicate_count: int


@router.post("/coverage", response_model=CoverageAnalysisResponse)
async def analyze_coverage(request: AnalyzeCoverageRequest):
    """Analyze test coverage for a Git repository."""
    try:
        analyzer = CoverageAnalyzer()
        result = await analyzer.analyze(
            git_repo_url=request.git_repo_url,
            branch=request.branch,
            test_directory=request.test_directory,
        )

        return CoverageAnalysisResponse(**result)
    except Exception as e:
        logger.error("Failed to analyze coverage", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duplicates", response_model=DuplicatesResponse)
async def find_duplicates(request: FindDuplicatesRequest):
    """Find duplicate tests in a Git repository."""
    try:
        finder = DuplicateFinder()
        result = await finder.find(
            git_repo_url=request.git_repo_url,
            branch=request.branch,
            test_directory=request.test_directory,
        )

        return DuplicatesResponse(**result)
    except Exception as e:
        logger.error("Failed to find duplicates", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

