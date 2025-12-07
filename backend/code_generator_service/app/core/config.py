"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "code-generator-service"
    DEBUG: bool = False
    POSTGRES_URL: str = "postgresql://testops:testops_password@localhost:5432/testops_db"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()

