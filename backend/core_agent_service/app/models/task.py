"""SQLAlchemy model for storing task metadata."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text

from app.db import Base


class TaskRecord(Base):
    """Persisted representation of a generated task."""

    __tablename__ = "tasks"

    task_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending")
    description = Column(Text, nullable=True)
    test_type = Column(String, nullable=True)
    feature = Column(String, nullable=True)
    story = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    owner_id = Column(String, nullable=True, index=True)
    jira_link = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_error = Column(Text, nullable=True)
    result_summary = Column(Text, nullable=True)
    progress_message = Column(Text, nullable=True)

    def update_status(
        self,
        status: str,
        error: Optional[str] = None,
        progress_message: Optional[str] = None,
        result_summary: Optional[str] = None,
    ) -> None:
        """Helper to update status-related fields."""
        self.status = status
        if error is not None:
            self.last_error = error
        if progress_message is not None:
            self.progress_message = progress_message
        if result_summary is not None:
            self.result_summary = result_summary


