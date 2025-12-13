"""GigaChat service for chat interactions."""

import httpx
import structlog
import asyncio
from typing import List, Dict, Any, Optional
from time import time
from collections import deque

from app.core.config import settings
from app.core.exceptions import LLMError

logger = structlog.get_logger()

# Максимальный контекст для GigaChat3: 262к токенов
MAX_CONTEXT_TOKENS = 262000
# Оставляем запас для ответа модели
RESERVED_TOKENS = 4000
# Максимальный контекст для запроса
MAX_REQUEST_TOKENS = MAX_CONTEXT_TOKENS - RESERVED_TOKENS

# Системный промпт для GigaChat
SYSTEM_PROMPT = """Ты — специализированный помощник для QA-разработчиков в сервисе автоматической генерации тестов.

ТВОЯ РОЛЬ:
1. Помогать создавать тесты трёх типов:
   - РУЧНЫЕ ТЕСТЫ: подробное описание шагов в формате Markdown (`.md`)
   - API-ТЕСТЫ: код на Python (`.py`) с использованием библиотеки requests + пояснение в `.md`
   - UI-ТЕСТЫ: код на Python (`.py`) с использованием selenium/playwright + пояснение в `.md`

2. Ты получаешь:
   - Исходный код приложения (Python, JavaScript, etc.)
   - Описание функциональности или требования
   - Файлы проекта для анализа
   - Конкретный запрос пользователя (например: "создай API-тест для эндпоинта /login")

3. Ты анализируешь материалы и генерируешь:
   - Чистый, готовый к запуску код на Python
   - Документацию в формате Markdown
   - Примеры использования
   - Обработку ошибок

ФОРМАТ ОТВЕТА:
- Для кода используй блоки ```python ... ```
- Для документации используй Markdown
- Если нужно несколько файлов, разделяй их заголовками ### Файл: filename.py

ПРАВИЛА:
1. Следуй best practices тестирования
2. Добавляй комментарии в код
3. Учитывай контекст проекта
4. Задавай уточняющие вопросы, если информации недостаточно
5. Помни контекст предыдущих сообщений в разговоре"""


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """Initialize rate limiter."""
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()

    async def acquire(self):
        """Acquire permission to make a request."""
        now = time()
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()

        if len(self.requests) >= self.max_requests:
            wait_time = self.time_window - (now - self.requests[0])
            if wait_time > 0:
                logger.warning("Rate limit reached, waiting", wait_time=wait_time)
                await asyncio.sleep(wait_time)
                while self.requests and self.requests[0] < time() - self.time_window:
                    self.requests.popleft()

        self.requests.append(time())


def estimate_tokens(text: str) -> int:
    """
    Оценить количество токенов в тексте.
    Примерная оценка: 1 токен ≈ 4 символа для русского/английского текста.
    """
    return len(text) // 4


def truncate_messages_to_fit(
    messages: List[Dict[str, str]], max_tokens: int
) -> tuple[List[Dict[str, str]], int]:
    """
    Обрезать сообщения, чтобы они поместились в лимит токенов.
    Всегда сохраняем системный промпт и последнее сообщение пользователя.
    
    Returns:
        (truncated_messages, total_tokens)
    """
    if not messages:
        return [], 0
    
    # Подсчитываем токены для каждого сообщения
    message_tokens = []
    total = 0
    
    for msg in messages:
        content = msg.get("content", "")
        tokens = estimate_tokens(content)
        message_tokens.append((msg, tokens))
        total += tokens
    
    # Если все помещается, возвращаем как есть
    if total <= max_tokens:
        return messages, total
    
    # Иначе обрезаем, начиная с самых старых (кроме системного и последнего)
    truncated = []
    current_tokens = 0
    
    # Всегда добавляем системный промпт
    system_prompt_tokens = estimate_tokens(SYSTEM_PROMPT)
    current_tokens += system_prompt_tokens
    
    # Добавляем сообщения с конца (последние важнее)
    for i in range(len(message_tokens) - 1, -1, -1):
        msg, tokens = message_tokens[i]
        
        # Если это системный промпт, пропускаем (уже учли)
        if msg.get("role") == "system":
            continue
        
        # Если это последнее сообщение пользователя, всегда добавляем
        if i == len(message_tokens) - 1 and msg.get("role") == "user":
            truncated.insert(0, msg)
            current_tokens += tokens
            continue
        
        # Проверяем, поместится ли
        if current_tokens + tokens <= max_tokens:
            truncated.insert(0, msg)
            current_tokens += tokens
        else:
            # Не помещается - обрезаем контент последнего сообщения
            if truncated:
                last_msg = truncated[0]
                available = max_tokens - current_tokens
                if available > 100:  # Минимум 100 токенов для обрезки
                    content = last_msg.get("content", "")
                    max_chars = available * 4
                    last_msg["content"] = content[:max_chars] + "... [сообщение обрезано]"
                    current_tokens += available
            break
    
    # Добавляем системный промпт в начало
    final_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + truncated
    
    return final_messages, current_tokens


class GigaChatService:
    """Service for interacting with GigaChat API."""

    def __init__(self, api_key: str | None = None, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize GigaChat service.

        Args:
            api_key: API key for GigaChat (if None, uses settings)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self.api_key = api_key or settings.CLOUD_RU_LLM_API_KEY
        self.api_url = settings.CLOUD_RU_LLM_API_URL
        self.model = "GigaChat/GigaChat3-10B-A1.8B"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        self.client = httpx.AsyncClient(
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Send chat message to GigaChat with context management.

        Args:
            messages: List of messages with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            Dict with 'content', 'model', 'usage', 'context_tokens', 'context_full'

        Raises:
            LLMError: If request fails
        """
        await self.rate_limiter.acquire()

        # Обрезаем сообщения, если нужно
        truncated_messages, context_tokens = truncate_messages_to_fit(
            messages, MAX_REQUEST_TOKENS
        )
        context_full = context_tokens >= MAX_REQUEST_TOKENS * 0.9  # 90% заполнен

        last_exception = None
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                payload = {
                    "model": self.model,
                    "messages": truncated_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "presence_penalty": 0,
                    "top_p": 0.95,
                }

                logger.info(
                    "Sending request to GigaChat API",
                    model=self.model,
                    attempt=attempt,
                    context_tokens=context_tokens,
                    context_full=context_full,
                )

                response = await self.client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()

                choices = result.get("choices")
                if not choices:
                    raise ValueError("Invalid API response: missing choices")

                message = choices[0].get("message", {})
                content = message.get("content", "")

                if not content:
                    raise ValueError("Empty response from GigaChat API")

                usage = result.get("usage", {})

                logger.info(
                    "GigaChat response received",
                    length=len(content),
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                )

                return {
                    "content": content,
                    "model": result.get("model", self.model),
                    "usage": usage,
                    "context_tokens": context_tokens,
                    "context_full": context_full,
                }

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code

                if 400 <= status_code < 500 and status_code != 429:
                    logger.error(
                        "Client error from GigaChat API",
                        status_code=status_code,
                        error=str(e),
                    )
                    raise LLMError(
                        f"GigaChat API error: {status_code}",
                        details={"status_code": status_code, "error": str(e)},
                    )

                if attempt < self.max_retries:
                    logger.warning(
                        "Retrying GigaChat API request",
                        attempt=attempt,
                        status_code=status_code,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logger.error(
                        "Max retries reached for GigaChat API",
                        status_code=status_code,
                        error=str(e),
                    )

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(
                        "Network error, retrying GigaChat API request",
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

        if last_exception:
            raise LLMError(
                "Failed to get response from GigaChat after all retry attempts",
                details={"error": str(last_exception), "max_retries": self.max_retries},
            )
        raise LLMError("Failed to get response from GigaChat after all retry attempts")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

