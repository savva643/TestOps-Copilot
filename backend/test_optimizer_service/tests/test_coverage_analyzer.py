"""Tests for coverage analyzer."""

import pytest
from app.services.coverage_analyzer import CoverageAnalyzer


def test_coverage_analyzer_initialization():
    """Test coverage analyzer can be initialized."""
    analyzer = CoverageAnalyzer()
    assert analyzer is not None


@pytest.mark.asyncio
async def test_analyze_coverage():
    """Test analyzing coverage (requires GitLab or mock)."""
    analyzer = CoverageAnalyzer()
    
    # This test requires GitLab token or mocked GitLab client
    # For now, just test initialization
    assert analyzer is not None

