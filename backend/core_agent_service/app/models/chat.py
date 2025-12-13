"""SQLAlchemy models for GigaChat sessions."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db import Base


class ChatSession(Base):
    """Chat session model for storing GigaChat conversations."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(String, nullable=True, index=True)  # User ID
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Сжатый контекст (оптимизированная версия истории)
    compressed_context = Column(Text, nullable=True)
    compressed_at = Column(DateTime, nullable=True)
    
    # Метаданные
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Связь с сообщениями
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, owner_id={self.owner_id})>"


class ChatMessage(Base):
    """Individual chat message model."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Метаданные
    tokens = Column(Integer, nullable=True)  # Примерное количество токенов
    
    # Связь с сессией
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role}, session_id={self.session_id})>"

