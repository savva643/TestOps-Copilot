"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "test-optimizer-service"
    DEBUG: bool = False
    POSTGRES_URL: str = "postgresql://testops:testops_password@localhost:5432/testops_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()

