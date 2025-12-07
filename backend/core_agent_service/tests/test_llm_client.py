"""Tests for LLM client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.services.llm_client import LLMClient, RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter():
    """Test rate limiter functionality."""
    limiter = RateLimiter(max_requests=2, time_window=1)
    
    # First two requests should pass immediately
    await limiter.acquire()
    await limiter.acquire()
    
    # Third request should wait
    import time
    start = time.time()
    await limiter.acquire()
    elapsed = time.time() - start
    
    # Should have waited at least a bit (allowing for timing variations)
    assert elapsed >= 0.5  # Should wait close to time_window


@pytest.mark.asyncio
async def test_llm_client_success():
    """Test successful LLM API call."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Generated test case content"
                }
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        client = LLMClient()
        result = await client.generate(
            system_prompt="Test system prompt",
            user_prompt="Test user prompt",
        )
        
        assert result == "Generated test case content"
        mock_post.assert_called_once()
        await client.close()


@pytest.mark.asyncio
async def test_llm_client_retry_on_server_error():
    """Test retry logic on server errors."""
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    mock_response_500.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error",
        request=MagicMock(),
        response=mock_response_500,
    )

    mock_response_success = MagicMock()
    mock_response_success.json.return_value = {
        "choices": [{"message": {"content": "Success after retry"}}]
    }
    mock_response_success.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call fails, second succeeds
        mock_post.side_effect = [
            mock_response_500,
            mock_response_success,
        ]
        
        client = LLMClient(max_retries=3, retry_delay=0.1)
        
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to speed up test
            result = await client.generate(
                system_prompt="Test",
                user_prompt="Test",
            )
        
        assert result == "Success after retry"
        assert mock_post.call_count == 2
        await client.close()


@pytest.mark.asyncio
async def test_llm_client_no_retry_on_client_error():
    """Test that client errors (4xx) are not retried."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad request",
        request=MagicMock(),
        response=mock_response,
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        client = LLMClient(max_retries=3)
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.generate(
                system_prompt="Test",
                user_prompt="Test",
            )
        
        # Should not retry on 4xx errors
        assert mock_post.call_count == 1
        await client.close()


@pytest.mark.asyncio
async def test_llm_client_empty_response():
    """Test handling of empty response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": ""}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        client = LLMClient()
        
        with pytest.raises(ValueError, match="Empty response"):
            await client.generate(
                system_prompt="Test",
                user_prompt="Test",
            )
        
        await client.close()


@pytest.mark.asyncio
async def test_llm_client_invalid_response_structure():
    """Test handling of invalid response structure."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # Missing "choices"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        client = LLMClient()
        
        with pytest.raises(ValueError, match="Invalid API response"):
            await client.generate(
                system_prompt="Test",
                user_prompt="Test",
            )
        
        await client.close()
