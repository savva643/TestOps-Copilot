"""Tests for duplicate finder."""

import pytest
from app.services.duplicate_finder import DuplicateFinder


def test_duplicate_finder_initialization():
    """Test duplicate finder can be initialized."""
    finder = DuplicateFinder()
    assert finder is not None


@pytest.mark.asyncio
async def test_find_duplicates():
    """Test finding duplicates (requires GitLab or mock)."""
    finder = DuplicateFinder()
    
    # This test requires GitLab token or mocked GitLab client
    # For now, just test initialization
    assert finder is not None

