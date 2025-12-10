"""Database setup and session utilities."""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# SQLAlchemy base and engine
Base = declarative_base()
engine = create_engine(settings.POSTGRES_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create database tables if they don't exist."""
    import app.models  # noqa: F401 - ensure models are registered with Base

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that provides a scoped session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Session:
    """Context manager for non-FastAPI usage (e.g., background tasks)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


