"""Service for compressing chat context using GigaChat."""

import structlog
from typing import List, Dict, Any

from app.services.gigachat_service import GigaChatService

logger = structlog.get_logger()

COMPRESSION_PROMPT = """Ты — помощник для оптимизации контекста чата.

ТВОЯ ЗАДАЧА:
Сжать историю разговора, сохранив только важную информацию:
1. Вопросы пользователя (кратко, суть)
2. Ключевые решения и ответы ассистента
3. Важные детали и контекст

УДАЛИ:
- Повторяющиеся вопросы
- Длинные объяснения (оставь суть)
- Несущественные детали

ФОРМАТ:
Верни сжатую версию в формате:
- Вопрос: [краткий вопрос]
- Решение: [ключевое решение/ответ]

История для сжатия:
{history}

Верни только сжатую версию, без дополнительных комментариев."""


class ChatCompressor:
    """Service for compressing chat history."""

    def __init__(self, gigachat_service: GigaChatService):
        """
        Initialize chat compressor.

        Args:
            gigachat_service: GigaChat service instance
        """
        self.gigachat_service = gigachat_service

    async def compress_messages(
        self, messages: List[Dict[str, str]], max_compression_ratio: float = 0.3
    ) -> str:
        """
        Compress chat messages using GigaChat.

        Args:
            messages: List of messages with 'role' and 'content'
            max_compression_ratio: Target compression ratio (0.3 = 30% of original)

        Returns:
            Compressed context as string
        """
        if not messages:
            return ""

        # Формируем историю для сжатия
        history_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                history_parts.append(f"Пользователь: {content}")
            elif role == "assistant":
                history_parts.append(f"Ассистент: {content}")

        history_text = "\n\n".join(history_parts)

        # Если история короткая, не сжимаем
        if len(history_text) < 1000:
            return history_text

        try:
            # Используем GigaChat для сжатия
            compression_messages = [
                {
                    "role": "system",
                    "content": COMPRESSION_PROMPT.format(history=history_text),
                }
            ]

            result = await self.gigachat_service.chat(
                messages=compression_messages,
                temperature=0.3,  # Низкая температура для более точного сжатия
                max_tokens=2000,
            )

            compressed = result["content"].strip()

            logger.info(
                "Chat compressed",
                original_length=len(history_text),
                compressed_length=len(compressed),
                ratio=len(compressed) / len(history_text) if history_text else 0,
            )

            return compressed

        except Exception as e:
            logger.error("Error compressing chat", error=str(e))
            # В случае ошибки возвращаем упрощенную версию
            return self._simple_compress(messages)

    def _simple_compress(self, messages: List[Dict[str, str]]) -> str:
        """
        Simple compression without AI (fallback).

        Args:
            messages: List of messages

        Returns:
            Simplified version
        """
        compressed_parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                # Берем первые 200 символов вопроса
                compressed_parts.append(f"Вопрос: {content[:200]}...")
            elif role == "assistant":
                # Берем первые 300 символов ответа
                compressed_parts.append(f"Ответ: {content[:300]}...")

        return "\n\n".join(compressed_parts)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4

