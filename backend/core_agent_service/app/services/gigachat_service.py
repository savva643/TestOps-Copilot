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

    def __init__(self, api_key: str | None = None, access_token: str | None = None, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize GigaChat service.

        Args:
            api_key: API key for GigaChat (for foundation-models API)
            access_token: IAM access token (for official GigaChat API)
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
        """
        self.api_key = api_key or settings.CLOUD_RU_LLM_API_KEY
        self.access_token = access_token
        self.api_url = settings.CLOUD_RU_LLM_API_URL
        self.gigachat_api_url = "https://gigachat.api.cloud.ru/api/gigachat/v1"
        self.project_id = "df406ab5-2b58-4027-a312-eb3c8c89e39d"
        # Список моделей для попыток (в порядке приоритета)
        self.models = [
            "ai-sage/GigaChat3-10B-A1.8B",  # Через foundation-models API
            "GigaChat/GigaChat-2-Max",       # Через foundation-models API
            settings.CLOUD_RU_LLM_MODEL,    # Fallback: openai/gpt-oss-120b
        ]
        self.current_model_index = 0
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = RateLimiter(max_requests=10, time_window=60)
        self.client = httpx.AsyncClient(timeout=120.0)

    async def _try_official_gigachat_api(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any] | None:
        """Попытка использовать официальный API GigaChat."""
        if not self.access_token:
            return None
        
        try:
            # Преобразуем сообщения в формат официального API
            api_messages = []
            for msg in messages:
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            payload = {
                "messages": api_messages,
                "model": "GigaChat",
                "options": {
                    "temperature": temperature,
                    "top_p": 0.95,
                    "max_tokens": max_tokens,
                    "repetition_penalty": 1.07,
                    "max_alternatives": 1
                },
                "project_id": self.project_id
            }
            
            # Для официального API GigaChat нужен токен без "Bearer "
            auth_token = self.access_token
            if auth_token.startswith("Bearer "):
                auth_token = auth_token.replace("Bearer ", "")
            
            response = await self.client.post(
                f"{self.gigachat_api_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": auth_token,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()
            
            # Обрабатываем ответ официального API
            alternatives = result.get("alternatives", [])
            if not alternatives:
                return None
            
            message = alternatives[0].get("message", {})
            content = message.get("content", "")
            if not content:
                return None
            
            usage = result.get("usage", {})
            model_info = result.get("model_info", {})
            
            return {
                "content": content,
                "model": model_info.get("name", "GigaChat"),
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                "context_tokens": usage.get("prompt_tokens", 0),
                "context_full": False,
            }
        except Exception as e:
            logger.warning("Official GigaChat API failed", error=str(e))
            return None

    async def _try_foundation_models_api(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        context_tokens: int,
        context_full: bool,
    ) -> Dict[str, Any] | None:
        """Попытка использовать foundation-models API."""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "presence_penalty": 0,
                "top_p": 0.95,
            }
            
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()
            
            choices = result.get("choices")
            if not choices:
                return None
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if not content:
                return None
            
            usage = result.get("usage", {})

            # Пытаемся использовать реальные токены из usage, если они есть
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

            # Некоторые модели могут возвращать только часть полей
            if total_tokens is None and prompt_tokens is not None:
                total_tokens = prompt_tokens + (completion_tokens or 0)

            effective_context_tokens = total_tokens or prompt_tokens or context_tokens
            
            return {
                "content": content,
                "model": result.get("model", model),
                "usage": usage,
                "context_tokens": effective_context_tokens,
                "context_full": context_full,
            }
        except Exception as e:
            logger.warning(f"Foundation-models API failed for model {model}", error=str(e))
            return None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Send chat message to GigaChat with context management.
        Пробует разные API и модели в порядке приоритета.

        Args:
            messages: List of messages with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            Dict with 'content', 'model', 'usage', 'context_tokens', 'context_full'

        Raises:
            LLMError: If all attempts fail
        """
        await self.rate_limiter.acquire()

        # Обрезаем сообщения, если нужно
        truncated_messages, context_tokens = truncate_messages_to_fit(
            messages, MAX_REQUEST_TOKENS
        )
        context_full = context_tokens >= MAX_REQUEST_TOKENS * 0.9  # 90% заполнен

        # 1. Пробуем официальный API GigaChat
        if self.access_token:
            logger.info("Trying official GigaChat API")
            result = await self._try_official_gigachat_api(
                truncated_messages, temperature, max_tokens
            )
            if result:
                logger.info("Official GigaChat API succeeded", model=result.get("model"))
                return result

        # 2. Пробуем модели через foundation-models API
        for model in self.models:
            logger.info("Trying foundation-models API", model=model)
            result = await self._try_foundation_models_api(
                model, truncated_messages, temperature, max_tokens, context_tokens, context_full
            )
            if result:
                logger.info("Foundation-models API succeeded", model=model)
                return result

        # Все попытки провалились
        raise LLMError(
            "Failed to get response from GigaChat. All API endpoints and models failed.",
            details={"models_tried": self.models, "has_access_token": bool(self.access_token)}
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

