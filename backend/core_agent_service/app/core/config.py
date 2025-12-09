"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings."""

    # Service configuration
    SERVICE_NAME: str = "core-agent-service"
    DEBUG: bool = False

    # Database
    POSTGRES_URL: str = "postgresql://testops:testops_password@localhost:5432/testops_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM API
    CLOUD_RU_LLM_API_KEY: str = ""
    CLOUD_RU_LLM_API_URL: str = "https://foundation-models.api.cloud.ru/v1"
    CLOUD_RU_LLM_MODEL: str = "openai/gpt-oss-120b"

    # External services
    SPEC_PARSER_URL: str = "http://localhost:8002"
    CODE_GENERATOR_URL: str = "http://localhost:8003"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()




