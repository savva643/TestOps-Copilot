"""LLM client for Cloud.ru Evolution Foundation Model."""

import httpx
import structlog
import asyncio
from typing import Dict, Any, Optional
from time import time
from collections import deque

from app.core.config import settings
from app.core.exceptions import LLMError

logger = structlog.get_logger()


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    async def acquire(self):
        """Acquire permission to make a request."""
        now = time()
        # Remove old requests outside the time window
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()

        # Check if we can make a request
        if len(self.requests) >= self.max_requests:
            # Wait until the oldest request expires
            wait_time = self.time_window - (now - self.requests[0])
            if wait_time > 0:
                logger.warning("Rate limit reached, waiting", wait_time=wait_time)
                await asyncio.sleep(wait_time)
                # Clean up again after waiting
                while self.requests and self.requests[0] < time() - self.time_window:
                    self.requests.popleft()

        self.requests.append(time())


class LLMClient:
    """Client for interacting with Cloud.ru Evolution Foundation Model API."""

    def __init__(self, api_key: str | None = None, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize LLM client.

        Args:
            api_key: API key for LLM (if None, uses settings)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self.api_key = api_key or settings.CLOUD_RU_LLM_API_KEY
        self.api_url = settings.CLOUD_RU_LLM_API_URL
        self.model = settings.CLOUD_RU_LLM_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate text using LLM with retry logic and rate limiting.

        Args:
            system_prompt: System prompt for the LLM
            user_prompt: User prompt/request
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            Generated text response

        Raises:
            httpx.HTTPError: If all retry attempts fail
            ValueError: If API response is invalid
        """
        # Apply rate limiting
        await self.rate_limiter.acquire()

        last_exception = None
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "presence_penalty": 0,
                    "top_p": 0.95,
                }

                logger.info(
                    "Sending request to LLM API",
                    api_url=self.api_url,
                    model=self.model,
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                response = await self.client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()

                # Validate response structure
                choices = result.get("choices")
                if not choices:
                    raise ValueError("Invalid API response: missing choices")

                def extract_content(choice: dict) -> str:
                    """Handle multiple response layouts from provider."""
                    # OpenAI-compatible shape
                    message = choice.get("message") or {}
                    content = message.get("content")
                    if isinstance(content, str):
                        return content.strip()
                    # Some providers wrap text in a list with {text: {value: ...}}
                    if isinstance(content, list):
                        parts = []
                        for item in content:
                            if isinstance(item, dict):
                                text_obj = item.get("text")
                                if isinstance(text_obj, dict):
                                    parts.append(str(text_obj.get("value", "")).strip())
                                elif isinstance(text_obj, str):
                                    parts.append(text_obj.strip())
                            elif isinstance(item, str):
                                parts.append(item.strip())
                        return "\n".join([p for p in parts if p])
                    # Legacy completion shape
                    text_fallback = choice.get("text")
                    if isinstance(text_fallback, str):
                        return text_fallback.strip()
                    return ""

                generated_text = extract_content(choices[0])

                if not generated_text:
                    # Include a small snippet of the raw payload for debugging
                    raise ValueError(
                        f"Empty response from LLM API (raw snippet: {str(result)[:200]})"
                    )

                logger.info(
                    "LLM response received",
                    length=len(generated_text),
                    attempt=attempt,
                )

                return generated_text

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                
                # Don't retry on client errors (4xx) except 429 (rate limit)
                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(
                        "Client error from LLM API",
                        status_code=status_code,
                        error=str(e),
                    )
                    raise
                
                # Retry on server errors (5xx) and rate limits (429)
                if attempt < self.max_retries:
                    logger.warning(
                        "Retrying LLM API request",
                        attempt=attempt,
                        status_code=status_code,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(
                        "Max retries reached for LLM API",
                        status_code=status_code,
                        error=str(e),
                    )

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "Network error, retrying LLM API request",
                        attempt=attempt,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error(
                        "Max retries reached due to network error",
                        error=str(e),
                    )

            except ValueError as e:
                # Don't retry on validation errors
                logger.error("Validation error in LLM response", error=str(e))
                raise LLMError(
                    "Invalid response from LLM API",
                    details={"error": str(e)},
                )

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "Unexpected error, retrying",
                        attempt=attempt,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error("Max retries reached", error=str(e))

        # If we get here, all retries failed
        if last_exception:
            raise LLMError(
                "Failed to generate text after all retry attempts",
                details={"error": str(last_exception), "max_retries": self.max_retries},
            )
        raise LLMError("Failed to generate text after all retry attempts")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()




