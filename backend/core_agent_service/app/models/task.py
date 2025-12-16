"""SQLAlchemy model for storing task metadata."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

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
    # GitLab integration fields
    gitlab_url = Column(String, nullable=True)
    gitlab_merge_request_url = Column(String, nullable=True)
    gitlab_branch = Column(String, nullable=True)
    gitlab_spec_path = Column(String, nullable=True)
    is_gitlab_task = Column(String, nullable=True, default="false")  # "true" or "false" as string

    # Связанные артефакты (сгенерированные файлы тестов)
    artifacts = relationship(
        "TaskArtifact",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

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


class TaskArtifact(Base):
    """Single test file (manual / API / UI) generated for a task.

    Мы явно храним текст, а не файлы: filename, описание и содержимое.
    """

    __tablename__ = "task_artifacts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String, ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    task = relationship("TaskRecord", back_populates="artifacts")


