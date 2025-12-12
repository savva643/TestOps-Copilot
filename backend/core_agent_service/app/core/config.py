"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
import json


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
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS_ORIGINS from environment variable."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Try to parse as JSON first
            try:
                if v.startswith('[') and v.endswith(']'):
                    return json.loads(v)
                elif v.startswith('"[') and v.endswith(']"'):
                    return json.loads(v[1:-1])
                elif v.startswith("'[") and v.endswith("]'"):
                    return json.loads(v[1:-1])
            except (json.JSONDecodeError, ValueError):
                pass
            # Fall back to comma-separated values
            return [origin.strip().strip('"').strip("'") for origin in v.split(',') if origin.strip()]
        return v


settings = Settings()




