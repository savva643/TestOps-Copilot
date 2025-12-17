"""GigaChat endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import structlog

from app.core.security import verify_api_key
from app.core.exceptions import LLMError
from app.services.gigachat_service import GigaChatService, MAX_CONTEXT_TOKENS
from app.services.chat_compressor import ChatCompressor
from app.db import get_db
from app.models.chat import ChatSession, ChatMessage as ChatMessageModel

logger = structlog.get_logger()

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat."""

    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: float = Field(0.5, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4000, ge=1, le=8000, description="Maximum tokens in response")
    session_id: Optional[str] = Field(None, description="Chat session ID (for persistence)")
    owner_id: Optional[str] = Field(None, description="User ID (for session management)")


class ChatResponse(BaseModel):
    """Response model for chat."""

    content: str = Field(..., description="Assistant's response")
    model: str = Field(..., description="Model used")
    usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    context_tokens: int = Field(..., description="Estimated tokens in context")
    context_full: bool = Field(..., description="Whether context is nearly full")
    context_percentage: float = Field(..., description="Context usage percentage (0-100)")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Send a message to GigaChat and get a response.
    
    This endpoint allows you to have a conversation with GigaChat AI assistant.
    The assistant remembers the conversation context and can help with:
    - Generating test cases (manual, API, UI)
    - Analyzing code
    - Creating test documentation
    
    **Context Management:**
    - Maximum context: 262,000 tokens (GigaChat3 model)
    - If context is nearly full (>90%), you'll need to clear the chat
    - Context usage is shown in the response
    
    **Rate Limiting:**
    - 10 requests per minute per API key
    
    **Example Request:**
    ```json
    {
        "messages": [
            {"role": "user", "content": "Создай API-тест для эндпоинта /login"}
        ],
        "temperature": 0.5,
        "max_tokens": 4000
    }
    ```
    """
    try:
        # Получаем LLM API ключ из заголовка (передается с фронтенда)
        llm_api_key = http_request.headers.get("X-LLM-API-Key")
        if not llm_api_key:
            raise HTTPException(
                status_code=400,
                detail="X-LLM-API-Key header is required. Please provide GigaChat API key.",
            )

        # Получаем access_token из Authorization заголовка (для официального API GigaChat)
        auth_header = http_request.headers.get("Authorization", "")
        access_token = None
        if auth_header.startswith("Bearer "):
            access_token = auth_header.replace("Bearer ", "")

        # Создаем сервис с пользовательским API ключом и токеном
        service = GigaChatService(api_key=llm_api_key, access_token=access_token)

        # Преобразуем сообщения в формат для сервиса
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Отправляем запрос
        result = await service.chat(
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        # Вычисляем процент заполнения контекста
        context_percentage = (result["context_tokens"] / MAX_CONTEXT_TOKENS) * 100

        # Сохраняем в БД, если указан session_id
        if request.session_id:
            try:
                # Получаем или создаем сессию
                session = db.query(ChatSession).filter(
                    ChatSession.session_id == request.session_id
                ).first()

                if not session:
                    session = ChatSession(
                        session_id=request.session_id,
                        owner_id=request.owner_id,
                    )
                    db.add(session)

                # Сохраняем последнее сообщение пользователя
                if request.messages:
                    last_user_msg = None
                    for msg in reversed(request.messages):
                        if msg.role == "user":
                            last_user_msg = msg
                            break

                    if last_user_msg:
                        user_msg = ChatMessageModel(
                            session_id=request.session_id,
                            role=last_user_msg.role,
                            content=last_user_msg.content,
                            tokens=estimate_tokens(last_user_msg.content),
                        )
                        db.add(user_msg)

                # Сохраняем ответ ассистента
                assistant_msg = ChatMessageModel(
                    session_id=request.session_id,
                    role="assistant",
                    content=result["content"],
                    tokens=result.get("usage", {}).get("completion_tokens", 0),
                )
                db.add(assistant_msg)

                # Обновляем метаданные сессии
                session.total_messages = db.query(ChatMessageModel).filter(
                    ChatMessageModel.session_id == request.session_id
                ).count()
                session.total_tokens = result["context_tokens"]
                session.updated_at = datetime.utcnow()

                db.commit()
            except Exception as e:
                logger.error("Error saving chat to DB", error=str(e))
                db.rollback()

        return ChatResponse(
            content=result["content"],
            model=result["model"],
            usage=result.get("usage"),
            context_tokens=result["context_tokens"],
            context_full=result["context_full"],
            context_percentage=round(context_percentage, 2),
        )

    except LLMError as e:
        # Ошибка от LLM API - передаем понятное сообщение
        logger.error(
            "LLM error in GigaChat chat endpoint",
            error=str(e),
            details=e.details if hasattr(e, 'details') else None,
        )
        error_message = str(e)
        if hasattr(e, 'details') and isinstance(e.details, dict):
            api_error = e.details.get('error', '')
            status_code = e.details.get('status_code', 0)
            if status_code == 404 or '404' in str(api_error) or '404' in error_message:
                error_message = (
                    "Модель GigaChat недоступна через foundation-models API. "
                    "Используется модель gpt-oss-120b. "
                    "Проверьте доступность модели GigaChat в вашем аккаунте Cloud.ru или используйте другую модель."
                )
            elif status_code == 401 or status_code == 403 or '401' in str(api_error) or '403' in str(api_error):
                error_message = "Ошибка авторизации API. Проверьте правильность API ключа Cloud.ru Evolution Model."
            elif status_code == 500 or '500' in str(api_error):
                error_message = "Ошибка сервера Cloud.ru API. Попробуйте позже."
        raise HTTPException(status_code=500, detail=error_message)
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except Exception as e:
        # Неожиданная ошибка
        logger.error(
            "Unexpected error in GigaChat chat endpoint",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)."""
    return len(text) // 4


@router.get("/chat/context-info")
async def get_context_info(
    http_request: Request,
    api_key: str = Depends(verify_api_key),
):
    """
    Get information about context limits.
    
    Returns:
        Information about maximum context size and recommendations.
    """
    return {
        "max_context_tokens": MAX_CONTEXT_TOKENS,
        "recommended_max_request_tokens": MAX_CONTEXT_TOKENS - 4000,
        "warning_threshold_percentage": 90,
        "model": "GigaChat/GigaChat3-10B-A1.8B",
        "description": "GigaChat3 model with 262k token context window",
    }


@router.post("/chat/{session_id}/compress")
async def compress_chat(
    session_id: str,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Compress chat history for a session.
    
    This endpoint compresses the chat history using GigaChat AI,
    keeping only important information (questions and solutions).
    """
    try:
        llm_api_key = http_request.headers.get("X-LLM-API-Key")
        if not llm_api_key:
            raise HTTPException(
                status_code=400,
                detail="X-LLM-API-Key header is required.",
            )

        # Получаем сессию
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Получаем все сообщения
        messages = db.query(ChatMessageModel).filter(
            ChatMessageModel.session_id == session_id
        ).order_by(ChatMessageModel.timestamp).all()

        if not messages:
            raise HTTPException(status_code=404, detail="No messages found in session")

        # Преобразуем в формат для сжатия
        messages_dict = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Сжимаем используя GigaChat
        gigachat_service = GigaChatService(api_key=llm_api_key)
        compressor = ChatCompressor(gigachat_service)
        compressed = await compressor.compress_messages(messages_dict)

        # Сохраняем сжатый контекст
        session.compressed_context = compressed
        session.compressed_at = datetime.utcnow()
        db.commit()

        return {
            "session_id": session_id,
            "compressed_context": compressed,
            "compressed_at": session.compressed_at.isoformat(),
            "original_messages": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error compressing chat", error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/chat/{session_id}/memory")
async def get_chat_memory(
    session_id: str,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Get compressed memory (context) for a chat session.
    
    Returns the optimized/compressed version of the chat history
    that GigaChat remembers.
    """
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return {
        "session_id": session_id,
        "compressed_context": session.compressed_context or "Память еще не сжата. Используйте /compress для оптимизации.",
        "compressed_at": session.compressed_at.isoformat() if session.compressed_at else None,
        "total_messages": session.total_messages,
        "total_tokens": session.total_tokens,
    }


@router.delete("/chat/{session_id}")
async def clear_chat_session(
    session_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Delete a chat session and all its messages from the database.

    Используется фронтендом при нажатии «Очистить чат», чтобы реально
    удалить историю, а не только очистить локальное состояние.
    """
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    db.delete(session)
    db.commit()

    return {"session_id": session_id, "status": "cleared"}
